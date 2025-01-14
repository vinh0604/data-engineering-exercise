from aws_cdk import Stack, Fn, Duration
from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_rds as rds,
    aws_glue as glue,
    aws_iam as iam
)

class MyETLBasicStack(Stack):
    def __init__(self, scope:Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Import shared resources from base stack
        vpc = ec2.Vpc.from_lookup(self, "Vpc",
            vpc_id=Fn.import_value("BaseVpcId")
        )
        
        bucket = s3.Bucket.from_bucket_name(self, "DataBucket",
            bucket_name=Fn.import_value("BaseBucketName")
        )
        
        db_endpoint = Fn.import_value("BaseDatabaseEndpoint")
        
        ec2_security_group = ec2.SecurityGroup.from_security_group_id(self, "Ec2Sg",
            security_group_id=Fn.import_value("BaseEc2SecurityGroupId")
        )

        # Glue Job Role
        glue_role = iam.Role(self, "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRDSFullAccess")
            ]
        )

        # Glue Job Security Group
        glue_security_group = ec2.SecurityGroup(self, "GlueSecurityGroup",
            vpc=vpc,
            description="Security group for Glue ETL job",
            allow_all_outbound=True
        )
        
        # Allow Glue to access RDS
        glue_security_group.connections.allow_to(
            ec2_security_group,
            ec2.Port.tcp(5432),
            "Allow Glue to access PostgreSQL"
        )

        # Glue Job
        glue_job = glue.CfnJob(self, "ChinookETLJob",
            name="chinook-etl-job",
            role=glue_role.role_arn,
            connections=glue.CfnJob.ConnectionsListProperty(
                connections=[f"{vpc.vpc_id}-{glue_security_group.security_group_id}"]
            ),
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=f"s3://{bucket.bucket_name}/scripts/chinook_etl.py"
            ),
            default_arguments={
                "--job-language": "python",
                "--enable-continuous-cloudwatch-log": "true",
                "--enable-metrics": "",
                "--TempDir": f"s3://{bucket.bucket_name}/temp/",
                "--job-bookmark-option": "job-bookmark-enable",
                "--extra-py-files": f"s3://{bucket.bucket_name}/libs/psycopg2-binary-2.9.6.tar.gz",
                "--DB_ENDPOINT": db_endpoint,
                "--DB_NAME": "chinook",
                "--DB_USER": "postgres",  # Replace with your actual DB username
                "--DB_PASSWORD": "password",  # Replace with your actual DB password
                "--OUTPUT_BUCKET": bucket.bucket_name
            },
            glue_version="3.0",
            worker_type="G.1X",
            number_of_workers=2,
            timeout=60
        )
