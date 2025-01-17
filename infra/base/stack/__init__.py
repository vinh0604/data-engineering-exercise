from aws_cdk import Stack, Duration, aws_ec2 as ec2, aws_rds as rds, aws_elasticloadbalancingv2 as elbv2, aws_s3 as s3, RemovalPolicy, CfnOutput
from aws_cdk import aws_elasticloadbalancingv2_targets as targets
import os
from constructs import Construct


class MyBaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Expose key resources as class properties
        self.vpc = None
        self.db = None
        self.bucket = None
        self.ec2_security_group = None
        self.db_security_group = None

        # Create VPC with both public and private subnets and IPv6 support
        self.vpc = ec2.Vpc(self, "MyVPC",
                           # 1024 IP addresses (10.0.0.0 - 10.0.3.255)
                           ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/22"),
                           max_azs=2,
                           nat_gateways=0,  # Need NAT gateway for private subnet internet access
                           ip_protocol=ec2.IpProtocol.DUAL_STACK,
                           subnet_configuration=[
                               ec2.SubnetConfiguration(
                                   name="Public",
                                   subnet_type=ec2.SubnetType.PUBLIC,
                                   cidr_mask=24,
                                   ipv6_assign_address_on_creation=True
                               ),
                               ec2.SubnetConfiguration(
                                   name="Private",
                                   subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                                   cidr_mask=24,
                                   ipv6_assign_address_on_creation=True
                               )
                           ]
                           )

        # Create security group for ALB
        alb_security_group = ec2.SecurityGroup(self, "ALBSecurityGroup",
                                               vpc=self.vpc,
                                               description="Security group for Application Load Balancer",
                                               allow_all_outbound=True,
                                                    allow_all_ipv6_outbound=True
                                               )
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP access from anywhere"
        )
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv6(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP access from anywhere IPv6"
        )

        # Create security group for EC2 instances with IPv6 support
        self.ec2_security_group = ec2.SecurityGroup(self, "EC2SecurityGroup",
                                                    vpc=self.vpc,
                                                    description="Security group for EC2 instances",
                                                    allow_all_outbound=True,
                                                    allow_all_ipv6_outbound=True
                                                    )
        # Allow EC2 Instance Connect
        self.ec2_security_group.add_ingress_rule(
            # AWS Instance Connect prefix list ID for IPv6 for ap-southeast-1
            peer=ec2.Peer.prefix_list('pl-000f9420a91cfc3b6'),
            connection=ec2.Port.tcp(22),
            description="Allow SSH access from EC2 Instance Connect"
        )
        # Allow HTTP access from ALB
        self.ec2_security_group.add_ingress_rule(
            peer=alb_security_group,
            connection=ec2.Port.tcp(80),
            description="Allow HTTP access from ALB"
        )

        # Create Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(self, "ALB",
                                            vpc=self.vpc,
                                            internet_facing=True,
                                            security_group=alb_security_group,
                                            ip_address_type=elbv2.IpAddressType.DUAL_STACK_WITHOUT_PUBLIC_IPV4
                                            )

        # Create EC2 instance with Docker installed and IPv6 support
        instance = ec2.Instance(self, "MetabaseInstance",
                                instance_type=ec2.InstanceType.of(
                                    ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
                                machine_image=ec2.MachineImage.latest_amazon_linux2(),
                                vpc=self.vpc,
                                vpc_subnets=ec2.SubnetSelection(
                                    subnet_type=ec2.SubnetType.PUBLIC),
                                security_group=self.ec2_security_group,
                                user_data=ec2.UserData.for_linux(),
                                block_devices=[
                                    ec2.BlockDevice(
                                        device_name="/dev/xvda",
                                        volume=ec2.BlockDeviceVolume.ebs(
                                            volume_size=20,
                                            volume_type=ec2.EbsDeviceVolumeType.GP3
                                        )
                                    )
                                ],
                                ipv6_address_count=1  # Enable primary IPv6 address
                                )
        # Add Docker installation and Metabase setup to user data
        instance.user_data.add_commands(
            "yum update -y",
            "amazon-linux-extras enable postgresql14",
            "yum install -y postgresql",
            "amazon-linux-extras install docker -y",
            "service docker start",
            "usermod -a -G docker ec2-user",
            # Read setup script content
            "cat <<MTL > /home/ec2-user/setup-metabase.sh",
            open(os.path.join(os.path.dirname(__file__),
                 "../../scripts/setup-metabase.sh")).read(),
            "MTL",
            "chmod +x /home/ec2-user/setup-metabase.sh",
            # enable Dual Stack endpoint for S3
            "aws configure set default.s3.use_dualstack_endpoint true"
        )

        # Add listener to ALB and target the EC2 instance
        listener = alb.add_listener("Listener",
                                    port=80,
                                    open=True
                                    )

        target_group = elbv2.ApplicationTargetGroup(self, "TargetGroup",
                                                    vpc=self.vpc,
                                                    port=80,
                                                    # targets=[targets.InstanceIdTarget(
                                                    #     instance_id=instance.instance_id, port=80)],
                                                    targets=[], # No targets initially, TODO: check missing primary IPv6 addresses issue
                                                    target_type=elbv2.TargetType.INSTANCE,
                                                    ip_address_type=elbv2.TargetGroupIpAddressType.IPV6,
                                                    health_check=elbv2.HealthCheck(
                                                        path="/api/health",
                                                        interval=Duration.seconds(
                                                            30),
                                                        timeout=Duration.seconds(
                                                            5)
                                                    )
                                                    )

        listener.add_target_groups("ListenerTargetGroup",
                                   target_groups=[target_group]
                                   )

        # Create security group for RDS
        self.db_security_group = ec2.SecurityGroup(self, "DatabaseSecurityGroup",
                                                   vpc=self.vpc,
                                                   description="Security group for RDS instance",
                                                   allow_all_outbound=True
                                                   )
        self.db_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(
                self.ec2_security_group.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access from within the same security group"
        )

        # Create S3 bucket for data engineering training
        self.bucket = s3.Bucket(self, "DataEngineerTrainingBucket",
                                bucket_name="vinh.dataengineertraining",
                                versioned=True,
                                encryption=s3.BucketEncryption.S3_MANAGED,
                                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                                removal_policy=RemovalPolicy.DESTROY,
                                auto_delete_objects=True
                                )

        # Create RDS instance
        self.db = rds.DatabaseInstance(self, "Database",
                                       engine=rds.DatabaseInstanceEngine.postgres(
                                           version=rds.PostgresEngineVersion.VER_13),
                                       instance_type=ec2.InstanceType.of(
                                           ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
                                       vpc=self.vpc,
                                       vpc_subnets=ec2.SubnetSelection(
                                           subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                                       security_groups=[
                                           self.db_security_group],
                                       allocated_storage=20,
                                       max_allocated_storage=100,
                                       publicly_accessible=False,
                                       removal_policy=RemovalPolicy.DESTROY,
                                       deletion_protection=False
                                       )

        # Export key resources for cross-stack references
        CfnOutput(self, "VpcId",
                  value=self.vpc.vpc_id,
                  export_name="BaseVpcId"
                  )

        CfnOutput(self, "BucketName",
                  value=self.bucket.bucket_name,
                  export_name="BaseBucketName"
                  )

        CfnOutput(self, "DatabaseEndpoint",
                  value=self.db.db_instance_endpoint_address,
                  export_name="BaseDatabaseEndpoint"
                  )

        CfnOutput(self, "Ec2SecurityGroupId",
                  value=self.ec2_security_group.security_group_id,
                  export_name="BaseEc2SecurityGroupId"
                  )

        CfnOutput(self, "DbSecurityGroupId",
                  value=self.db_security_group.security_group_id,
                  export_name="BaseDbSecurityGroupId"
                  )
