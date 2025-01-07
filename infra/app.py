#!/usr/bin/env python3
import aws_cdk as cdk
from stack.stack import MyStack

app = cdk.App()

env = cdk.Environment(
    account="YOUR_AWS_ACCOUNT_ID",  # Replace with your AWS account ID
    region="us-east-1"              # Replace with your preferred AWS region
)

MyStack(app, "MyStack", env=env)

app.synth()
