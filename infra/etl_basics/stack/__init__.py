from aws_cdk import Stack
from constructs import Construct

class MyETLBasicStack(Stack):
    def __init__(self, scope:Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
