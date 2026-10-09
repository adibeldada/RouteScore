from aws_cdk import (
    BundlingOptions,
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3 as s3,
)
from constructs import Construct


class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- STORAGE ---
        # S3 bucket: cloud storage for every raw feed snapshot.
        # It's just an empty "folder" — handler.py is what puts files in it.
        # Files are auto-deleted after 90 days to keep costs down.
        bucket = s3.Bucket(
            self, "RawFeedBucket",
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(90)),
            ],
        )

        # --- THE CODE ---
        # Lambda: runs src/handler.py (lambda_handler) in the cloud.
        # Created after the bucket so it can be told the bucket's name.
        fetch_fn = _lambda.Function(
            self, "FetchFeedFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="handler.lambda_handler",          # file.function to call
            code=_lambda.Code.from_asset(
                "../src",                              # folder to upload (relative to infra/)
                bundling=BundlingOptions(              # install src/requirements.txt in Docker
                    image=_lambda.Runtime.PYTHON_3_13.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                ),
            ),
            timeout=Duration.seconds(30),              # default is 3 s, too short
            memory_size=256,
            environment={                              # values handler.py can read
                "BUCKET_NAME": bucket.bucket_name,     # auto-generated name, passed in
            },
        )

        # --- PERMISSION ---
        # Allow the Lambda to upload files into this bucket (and nothing else).
        bucket.grant_put(fetch_fn)

        # --- THE TIMER ---
        # EventBridge rule: calls the Lambda every 1 minute.
        rule = events.Rule(
            self, "EveryMinute",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            targets=[targets.LambdaFunction(fetch_fn)],
        )