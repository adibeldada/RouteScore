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

dynamodb = boto3.resource("dynamodb")                                   # connect to DynamoDB
table = dynamodb.Table("RouteScoreStack-StatsTableV3CD71D0CC-FCBS2KYLLJX3")   # handle to the V3 table

def pct(part, total):
    """Percent, safe if total is 0."""
    return round(part / total * 100, 1) if total else 0

def get_route(route_id):
    response = table.query(KeyConditionExpression=Key("pk").eq("ROUTE#"+route_id))
    rows = response["Items"]

    overall = None # sameish as overall = {}, its just null while {} is a null
    hours = []

    for row in rows:
        sk = row["sk"]
        early = int(row["early"])                      # DynamoDB gives Decimal -> int
        on_time = int(row["on_time"])
        late = int(row["late"])
        total = int(row["total"])


        if sk == "ALL":
            overall = {
                "on_time": pct(on_time, total),
                "late": pct(late, total),
                "early": pct(early, total),
                "total": total,
            }
        
        if sk.startswith("HOUR#"):
            hours.append({
                "hour": sk.replace("HOUR#", ""),
                "on_time": pct(on_time, total),
                "late": pct(late, total),
                "early": pct(early, total),
                "total": total,
            })
    
    result = {
        "route_id": route_id,
        "overall": overall,
        "hours": hours,
    }

    return result

def get_route_day(route_id, day):
    response = table.query(KeyConditionExpression=Key("pk").eq("DAY#"+day) & Key("sk").eq("ROUTE#"+route_id))
    rows = response["Items"]

    if not rows:
       return None
    
    row = rows[0]   

    early = int(row["early"])                      # DynamoDB gives Decimal -> int
    on_time = int(row["on_time"])
    late = int(row["late"])
    total = int(row["total"])

    result = {
        "route_id": route_id,
        "day": day,
        "on_time": pct(on_time, total),
        "late": pct(late, total),
        "early": pct(early, total),
        "total": total,
    }

    return result

def get_home()
    response = table.query(KeyConditionExpression=Key("pk").eq("DAY#"+day) & Key("sk").eq("ROUTE#"+route_id))
    rows = response["Items"]

if __name__ == "__main__":
    print(get_route("5807"))
    print(get_route_day("5807", "2026-10-21"))
    print(get_route_day("5807", "2020-01-01"))

        
 
        