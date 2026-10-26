"""
api.py

API for the v0.4 dashboard. The middleman between the website and DynamoDB.

The browser can't read DynamoDB directly, so these functions read the stats
table and return only what each page needs (as dicts, later sent as JSON).

get_route(route_id): overall % + hour-by-hour % for one route (route page)
Coming: get_leaderboard(), get_stop(stop_id), lambda_handler
"""

import boto3                                   # talk to DynamoDB
from boto3.dynamodb.conditions import Key      # build the query condition: Key("pk").eq(...)