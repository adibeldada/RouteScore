"""
api.py

API for the v0.4 dashboard. The middleman between the website and DynamoDB.

The browser can't read DynamoDB directly, so these functions read the stats
table and return only what each page needs (as dicts, later sent as JSON).

get_route(route_id):          overall % + hour-by-hour % for one route (route page)
get_route_day(route_id, day): one route on one day (Days tab)
get_home():                   all of Hamilton combined (main screen)
get_leaderboard():            main routes, best to worst (main screen)
get_stop(stop_id):            one stop, all routes combined (stop lookup)
Coming: lambda_handler
"""

# Paths the website can call (I designed these; frontend must use the same ones):
#   /home                          -> get_home()                    all of Hamilton
#   /leaderboard                   -> get_leaderboard()             main routes, best -> worst
#   /routes/<route_id>             -> get_route(route_id)           e.g. /routes/5828
#   /routes/<route_id>/days/<day>  -> get_route_day(route_id, day)  e.g. /routes/5828/days/2026-10-21
#   /stops/<stop_id>               -> get_stop(stop_id)             e.g. /stops/2345
#   anything else                  -> 404 {"error": "not found"}

import boto3                                        # talk to DynamoDB
from boto3.dynamodb.conditions import Key, Attr     # Key = query conditions, Attr = scan filters

import json 
import os

dynamodb = boto3.resource("dynamodb")                                         # connect to DynamoDB
table = dynamodb.Table(os.environ.get("TABLE_NAME", "RouteScoreStack-StatsTableV3CD71D0CC-FCBS2KYLLJX3"))

MIN_ROUTE_ARRIVALS = 10000      # leaderboard only counts main routes (skips tiny/special services)


def pct(part, total):
    """Percent, safe if total is 0."""
    return round(part / total * 100, 1) if total else 0


def scan_all(filter_expression):
    """Scan the whole table, following LastEvaluatedKey so nothing is missed.

    DynamoDB returns at most 1 MB per scan call (measured BEFORE the filter),
    so one call can quietly return only part of the table.
    """
    response = table.scan(FilterExpression=filter_expression)
    rows = response["Items"]
    while "LastEvaluatedKey" in response:                      # more data left?
        response = table.scan(FilterExpression=filter_expression,
                              ExclusiveStartKey=response["LastEvaluatedKey"])   # continue where it stopped
        rows.extend(response["Items"])                         # add this page's rows to the list
    return rows


def get_route(route_id):
    response = table.query(KeyConditionExpression=Key("pk").eq("ROUTE#" + route_id))
    rows = response["Items"]

    overall = None      # None = no ALL row found yet (null in JSON)
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

        elif sk.startswith("HOUR#"):
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
    response = table.query(KeyConditionExpression=Key("pk").eq("DAY#" + day) & Key("sk").eq("ROUTE#" + route_id))
    rows = response["Items"]

    if not rows:
        return None

    row = rows[0]       # pk + sk match at most one row

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


def get_home():
    rows = scan_all(Attr("pk").begins_with("ROUTE#") & Attr("sk").eq("ALL"))   # every route's all-time row

    system = {"early": 0, "on_time": 0, "late": 0, "total": 0}   # all of Hamilton combined
    for row in rows:
        system["early"] += int(row["early"])       # DynamoDB gives Decimal -> int
        system["on_time"] += int(row["on_time"])
        system["late"] += int(row["late"])
        system["total"] += int(row["total"])

    system_result = {
        "on_time": pct(system["on_time"], system["total"]),
        "late": pct(system["late"], system["total"]),
        "early": pct(system["early"], system["total"]),
        "total": system["total"],
    }

    return system_result


def get_leaderboard():
    rows = scan_all(Attr("pk").begins_with("ROUTE#") & Attr("sk").eq("ALL"))   # every route's all-time row

    leaderboard = []

    for row in rows:
        total = int(row["total"])
        if total < MIN_ROUTE_ARRIVALS:              # skip tiny/special routes
            continue

        early = int(row["early"])                  # DynamoDB gives Decimal -> int
        on_time = int(row["on_time"])
        late = int(row["late"])

        leaderboard.append({
            "route_id": row["pk"].replace("ROUTE#", ""),   # "ROUTE#5828" -> "5828"
            "on_time": pct(on_time, total),
            "late": pct(late, total),
            "early": pct(early, total),
            "total": total,
        })

    leaderboard.sort(key=lambda r: r["on_time"], reverse=True)   # best -> worst
    return leaderboard


def get_stop(stop_id):
    # Both keys are known, so ask for exactly this stop's row (no scan)
    response = table.query(KeyConditionExpression=Key("pk").eq("STOP#" + stop_id) & Key("sk").eq("ALL"))
    rows = response["Items"]

    if not rows:
        return None

    row = rows[0]       # pk + sk match at most one row

    early = int(row["early"])                      # DynamoDB gives Decimal -> int
    on_time = int(row["on_time"])
    late = int(row["late"])
    total = int(row["total"])

    result = {
        "stop_id": stop_id,
        "on_time": pct(on_time, total),
        "late": pct(late, total),
        "early": pct(early, total),
        "total": total,
    }

    return result


def respond(status, body):
    """Wrap data in the format API Gateway expects. its a helper funciton"""
    return {
        "statusCode": status,                              # 200 = OK, 404 = not found
        "headers": {"Access-Control-Allow-Origin": "*"},   # CORS: let the website read it
        "body": json.dumps(body),                          # body must be text, not a dict
    }


# event = the request, built by API Gateway, e.g. for https://.../routes/5828:
# {
#     "resource": "/{proxy+}",
#     "path": "/routes/5828",                   ← the only part I use
#     "httpMethod": "GET",                      ← GET = just reading
#     "headers": {"Host": "abc123.execute-api.ca-central-1.amazonaws.com", ...},
#     "queryStringParameters": None,            ← anything after ? in the URL (none here)
#     "pathParameters": {"proxy": "routes/5828"},
#     "requestContext": {"stage": "prod", ...}, ← info about the request
#     "body": None,                             ← GET requests have no body
# }
#
# context = info about this Lambda run (request id, time left). Not used.
#
# To test on my laptop, a fake event with just the path is enough:
#     lambda_handler({"path": "/routes/5807"}, None)
def lambda_handler(event, context):
    parts = event["path"].strip("/").split("/")    # "/routes/5828" -> ["routes", "5828"]

    # /home -> get_home()
    if len(parts) == 1 and parts[0] == "home":
        result = get_home()
        return respond(200, result)

    # /leaderboard -> get_leaderboard()
    elif len(parts) == 1 and parts[0] == "leaderboard":
        result = get_leaderboard()
        return respond(200, result)

    # /routes/<route_id> -> get_route(route_id)
    elif len(parts) == 2 and parts[0] == "routes":
        route_id = parts[1]
        result = get_route(route_id)
        if result["overall"] is None:                       # no such route
            return respond(404, {"error": "not found"})
        return respond(200, result)

    # /routes/<route_id>/days/<day> -> get_route_day(route_id, day)
    elif len(parts) == 4 and parts[0] == "routes" and parts[2] == "days":
        route_id = parts[1]
        day = parts[3]
        result = get_route_day(route_id, day)
        if result is None:                                  # no data that day
            return respond(404, {"error": "not found"})
        return respond(200, result)

    # /stops/<stop_id> -> get_stop(stop_id)
    elif len(parts) == 2 and parts[0] == "stops":
        stop_id = parts[1]
        result = get_stop(stop_id)
        if result is None:                                  # no such stop
            return respond(404, {"error": "not found"})
        return respond(200, result)

    return respond(404, {"error": "not found"})             # path didn't match anything
    

if __name__ == "__main__":
    print(get_route("5807"))
    print(get_route_day("5807", "2026-10-21"))
    print(get_route_day("5807", "2020-01-01"))   # no data -> None
    print(get_home())
    print(get_leaderboard())
    print(get_stop("1001"))                     
    print(get_stop("0"))                         # not a stop -> None
    print(lambda_handler({"path": "/home"}, None))
    print(lambda_handler({"path": "/leaderboard"}, None))
    print(lambda_handler({"path": "/routes/5807"}, None))
    print(lambda_handler({"path": "/routes/5807/days/2026-10-21"}, None))
    print(lambda_handler({"path": "/stops/1001"}, None))       # real stop id
    print(lambda_handler({"path": "/stops/0"}, None))          # → 404
    print(lambda_handler({"path": "/banana"}, None))           # → 404