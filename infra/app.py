#!/usr/bin/env python3
import aws_cdk as cdk
from stack import MyStack

app = cdk.App()

env = cdk.Environment(
    account="992382816481",
    region="ap-southeast-1"
)

MyStack(app, "MyStack", env=env)

app.synth()
