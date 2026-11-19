from aws_cdk import (
    BundlingOptions,                 # how to package src/ (pip install inside a Lambda-like Docker container)
    CfnOutput,                       # print a value (the API URL, the site URL) after cdk deploy
    Duration,                        # time values: Duration.seconds(10), Duration.minutes(5), Duration.days(90)
    RemovalPolicy,                   # what happens to a resource when the stack is deleted (keep or destroy)
    Stack,                           # the base class InfraStack builds on (one deployable group of AWS resources)
    aws_lambda as _lambda,           # Lambda functions (fetch, process, api) + their code and runtime
    aws_events as events,            # EventBridge rules: the timers (every minute, every hour)
    aws_events_targets as targets,   # what a rule runs: targets.LambdaFunction(fetch_fn)
    aws_s3 as s3,                    # S3 buckets: data (raw/, arrivals/) and the website files
    aws_dynamodb as dynamodb,        # DynamoDB stats table
    aws_apigateway as apigateway,    # API Gateway: gives api_fn a URL
    aws_cloudfront as cloudfront,             # CloudFront: serves the site over HTTPS + caches it worldwide
    aws_cloudfront_origins as origins,        # tells CloudFront where the files come from (my S3 bucket)
    aws_s3_deployment as s3deploy,            # uploads my frontend/ folder into the bucket on every cdk deploy
)
from constructs import Construct     # the type for "scope": every CDK piece is a Construct


class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- STORAGE ---
        # Data bucket: raw/ = every minute's feed, arrivals/ = every hour's results.
        # raw/ files are auto-deleted after 90 days to keep costs down.
        bucket = s3.Bucket(
            self, "RawFeedBucket",
            lifecycle_rules=[
                s3.LifecycleRule(prefix="raw/", expiration=Duration.days(90)),   # only raw snapshots expire
            ],
        )

        # Stats table: running on-time totals by route, stop, hour and day.
        table = dynamodb.Table(
            self, "StatsTableV3",
            partition_key = dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key = dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # Site bucket: holds the website files (index.html, app.js, style.css).
        # Separate from the data bucket so the site deploy can never touch raw/ or arrivals/.
        site_bucket = s3.Bucket(
            self, "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,   # nobody can read the bucket directly, only CloudFront
            removal_policy=RemovalPolicy.DESTROY,                 # if I delete the stack, delete this bucket too
            auto_delete_objects=True,                             # empty it first (AWS won't delete a bucket that has files)
        )

        # --- THE CODE (shared) ---
        # All three Lambdas run code from the same src/ folder, so package it once.
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
        # This is EventBridge 1 (targets.LambdaFunction(fetch_fn)) is what runs it every minute
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
        # This is EventBridge 2 (targets.LambdaFunction(process_fn)) is what runs it every hour
        hourly_rule = events.Rule(
            self, "EveryHour",
            schedule=events.Schedule.cron(minute="5"),
            targets=[targets.LambdaFunction(process_fn)],
        )

        # --- LAMBDA 3: API ---
        # Runs src/api.py: answers website requests by reading the stats table.
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
            deploy_options=apigateway.StageOptions(
                throttling_rate_limit=10,     # max 10 requests/second on average
                throttling_burst_limit=20,    # allow short bursts up to 20 at once
            ),
        )

        # --- WEBSITE (CloudFront in front of site_bucket) ---
        # CloudFront gives the site an HTTPS link and caches it; only it can read site_bucket.
        distribution = cloudfront.Distribution(
            self, "SiteDistribution",
            default_behavior=cloudfront.BehaviorOptions(                                   # how CloudFront handles every request
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),    # get files from site_bucket (only CloudFront may read it)
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,  # http:// → https://
            ),
            default_root_object="index.html",                                              # bare link opens index.html
        )

        # Upload frontend/ into site_bucket on every cdk deploy, then clear CloudFront's cache.
        s3deploy.BucketDeployment(
            self, "DeploySite",
            sources=[s3deploy.Source.asset("../frontend")],   # what to upload: my frontend/ folder
            destination_bucket=site_bucket,                   # where it goes
            distribution=distribution,                        # after uploading, clear CloudFront's cache...
            distribution_paths=["/*"],                        # ...for every file, so changes show up right away
        )

        # --- OUTPUTS ---
        # Printed after cdk deploy.
        CfnOutput(self, "ApiUrl", value=api.url)                                            # the API's URL
        CfnOutput(self, "SiteUrl", value="https://" + distribution.distribution_domain_name) # the website's URL