import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="data_engineering_infra",
    version="0.0.1",
    description="AWS CDK for Data Engineering Exercises",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="author",
    package_dir={"": "stack"},
    packages=setuptools.find_packages(where="stack"),
    install_requires=[
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
    ],
    python_requires=">=3.6",
)
