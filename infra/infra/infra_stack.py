from aws_cdk import (
    BundlingOptions,
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct


class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
        )

        rule = events.Rule(
            self, "EveryMinute",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            targets=[targets.LambdaFunction(fetch_fn)],
        )
        