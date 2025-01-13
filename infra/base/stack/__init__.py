from aws_cdk import Stack, aws_ec2 as ec2, aws_rds as rds, aws_autoscaling as autoscaling, aws_elasticloadbalancingv2 as elbv2, aws_s3 as s3, RemovalPolicy
import os
from constructs import Construct

class MyBaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC with both public and private subnets and IPv6 support
        vpc = ec2.Vpc(self, "MyVPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/22"),  # 1024 IP addresses (10.0.0.0 - 10.0.3.255)
            max_azs=2,
            nat_gateways=0,  # Need NAT gateway for private subnet internet access
            ip_protocol=ec2.IpProtocol.DUAL_STACK,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )

        # Create security group for ALB
        alb_security_group = ec2.SecurityGroup(self, "ALBSecurityGroup",
            vpc=vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True
        )
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP access from anywhere"
        )

        # Create security group for EC2 instances with IPv6 support
        ec2_security_group = ec2.SecurityGroup(self, "EC2SecurityGroup",
            vpc=vpc,
            description="Security group for EC2 instances",
            allow_all_outbound=True
        )
        # Allow EC2 Instance Connect
        ec2_security_group.add_ingress_rule(
            peer=ec2.Peer.prefix_list('pl-073f7512b7b9a2450'), # AWS Instance Connect prefix list ID for IPv4 for ap-southeast-1
            connection=ec2.Port.tcp(22),
            description="Allow SSH access from EC2 Instance Connect"
        )

        # Create Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(self, "ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group
        )

        # Add listener to ALB
        listener = alb.add_listener("Listener",
            port=80,
            open=True
        )

        # Create Launch Template with Docker installed and IPv6 support
        launch_template = ec2.LaunchTemplate(self, "LaunchTemplate",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            security_group=ec2_security_group,
            user_data=ec2.UserData.for_linux(),
            associate_public_ip_address=False,
            ipv6_addressing=True,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=20,
                        volume_type=ec2.EbsDeviceVolumeType.GP3
                    )
                )
            ]
        )
        # Add Docker installation and Metabase setup to user data
        launch_template.user_data.add_commands(
            "yum update -y",
            "amazon-linux-extras install docker -y",
            "service docker start",
            "usermod -a -G docker ec2-user",
            # Read setup script content
            "cat <<MTL > /home/ec2-user/setup-metabase.sh",
            open(os.path.join(os.path.dirname(__file__), "../scripts/setup-metabase.sh")).read(),
            "MTL",
            "chmod +x /home/ec2-user/setup-metabase.sh"
        )

        # Create Auto Scaling Group
        asg = autoscaling.AutoScalingGroup(self, "ASG",
            vpc=vpc,
            launch_template=launch_template,
            min_capacity=1,
            max_capacity=1,
            desired_capacity=1,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )

        # Add ASG to ALB target group
        listener.add_targets("ApplicationFleet",
            port=80,
            targets=[asg]
        )

        # Create security group for RDS
        db_security_group = ec2.SecurityGroup(self, "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for RDS instance",
            allow_all_outbound=True
        )
        db_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(ec2_security_group.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access from within the same security group"
        )

        # Create S3 bucket for data engineering training
        bucket = s3.Bucket(self, "DataEngineerTrainingBucket",
            bucket_name="vinh.dataengineertraining",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Create RDS instance
        db = rds.DatabaseInstance(self, "Database",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_13),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[db_security_group],
            allocated_storage=20,
            max_allocated_storage=100,
            publicly_accessible=False,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False
        )

