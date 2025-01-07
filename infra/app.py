#!/usr/bin/env python3
import aws_cdk as cdk
from stack.stack import MyStack

app = cdk.App()
MyStack(app, "MyStack")

app.synth()
