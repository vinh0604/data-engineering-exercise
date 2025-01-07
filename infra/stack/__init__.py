from aws_cdk import Stack, aws_ec2 as ec2, aws_rds as rds, RemovalPolicy
from constructs import Construct

class MyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC with both public and private subnets
        vpc = ec2.Vpc(self, "MyVPC",
            max_azs=1,
            nat_gateways=1,  # Need NAT gateway for private subnet internet access
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                    cidr_mask=24
                )
            ]
        )

        # Create security group for RDS
        db_security_group = ec2.SecurityGroup(self, "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for RDS instance",
            allow_all_outbound=True
        )
        db_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access"
        )

        # Create RDS instance
        db = rds.DatabaseInstance(self, "Database",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_13),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[db_security_group],
            allocated_storage=20,
            max_allocated_storage=100,
            publicly_accessible=True,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False
        )

