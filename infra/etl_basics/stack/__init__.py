from aws_cdk import Stack, Fn
from constructs import Construct
from aws_cdk import aws_ec2 as ec2, aws_s3 as s3, aws_rds as rds

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
