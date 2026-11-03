from aws_cdk import (
    BundlingOptions,                 # how to package src/ (pip install inside a Lambda-like Docker container)
    CfnOutput,                       # print a value (the API URL) after cdk deploy
    Duration,                        # time values: Duration.seconds(10), Duration.minutes(5), Duration.days(90)
    Stack,                           # the base class InfraStack builds on (one deployable group of AWS resources)
    aws_lambda as _lambda,           # Lambda functions (fetch, process, api) + their code and runtime
    aws_events as events,            # EventBridge rules: the timers (every minute, every hour)
    aws_events_targets as targets,   # what a rule runs: targets.LambdaFunction(fetch_fn)
    aws_s3 as s3,                    # S3 bucket for raw/ and arrivals/
    aws_dynamodb as dynamodb,        # DynamoDB stats table
    aws_apigateway as apigateway,    # API Gateway: gives api_fn a URL
)
from constructs import Construct     # the type for "scope": every CDK piece is a Construct


class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- STORAGE ---
        # S3 bucket: raw/ = every minute's feed, arrivals/ = every hour's results.
        # Files are auto-deleted after 90 days to keep costs down.
        bucket = s3.Bucket(
            self, "RawFeedBucket",
            lifecycle_rules=[
                s3.LifecycleRule(prefix="raw/", expiration=Duration.days(90)),   # only raw snapshots expire
            ],
        )

        table = dynamodb.Table(
            self, "StatsTableV3",
            partition_key = dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key = dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, 

        )

        # --- THE CODE (shared) ---
        # Both Lambdas run code from the same src/ folder, so package it once.
        # Installs src/requirements.txt inside a Lambda-like Docker container.
        code = _lambda.Code.from_asset(
            "../src",
            bundling=BundlingOptions(
                image=_lambda.Runtime.PYTHON_3_13.bundling_image,
                command=[
                    "bash", "-c",
                    "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                ],
            ),
        )

        # --- LAMBDA 1: FETCH (every minute) ---
        # Runs src/handler.py: downloads the live feed and saves it to raw/.
        fetch_fn = _lambda.Function(
            self, "FetchFeedFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="handler.lambda_handler",
            code=code,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "BUCKET_NAME": bucket.bucket_name,
            },
        )

        # Fetch only needs to upload to the bucket.
        bucket.grant_put(fetch_fn)

        # Timer: call the fetch Lambda every 1 minute.
        # This is EventBridge 1 (targets.lambdaFunciton(fetch_fn)) is what runs it every minute
        rule = events.Rule(
            self, "EveryMinute",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            targets=[targets.LambdaFunction(fetch_fn)],
        )

        # --- LAMBDA 2: PROCESS (every hour) ---
        # Runs src/process.py: reads the last hour from raw/, finds final arrivals,
        # saves them to arrivals/.
        process_fn = _lambda.Function(
            self, "ProcessArrivalsFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="process.lambda_handler",
            code=code,
            timeout=Duration.minutes(5),               # ~60 files to download + process
            memory_size=2048,                          # holds an hour of feeds in memory (more memory = faster too)
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "TABLE_NAME" : table.table_name
            },
        )

        # Process needs to read raw/ and write arrivals/.
        bucket.grant_read(process_fn)
        bucket.grant_put(process_fn)
        table.grant_read_write_data(process_fn)

        # Timer: call the process Lambda at 5 minutes past every hour
        # (gives the last snapshot of the previous hour time to land first).
        # This is EventBridge 2 (targets.lambdaFunciton(process_fn)) is what runs it every hour
        hourly_rule = events.Rule(
            self, "EveryHour",
            schedule=events.Schedule.cron(minute="5"),
            targets=[targets.LambdaFunction(process_fn)],
        )

        # --- LAMBDA 3 ---
        api_fn = _lambda.Function(
            self, "ApiFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="api.lambda_handler",
            code=code,
            timeout=Duration.seconds(10),
            memory_size=256,
            environment={
                "TABLE_NAME" : table.table_name
            },
        )

        # api_fn needs to be able to read the table
        table.grant_read_data(api_fn)       # API only reads the stats table

        # API Gateway: gives api_fn a URL. Every path (/home, /routes/5828, ...)
        # is sent to api_fn's lambda_handler, which decides what to do.
        api = apigateway.LambdaRestApi(
            self, "RouteScoreApi",
            handler=api_fn,
        )

        # Print the API's URL after cdk deploy
        CfnOutput(self, "ApiUrl", value=api.url)