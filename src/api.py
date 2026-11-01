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

import boto3                                        # talk to DynamoDB
from boto3.dynamodb.conditions import Key, Attr     # Key = query conditions, Attr = scan filters

dynamodb = boto3.resource("dynamodb")                                         # connect to DynamoDB
table = dynamodb.Table("RouteScoreStack-StatsTableV3CD71D0CC-FCBS2KYLLJX3")   # handle to the V3 table

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


if __name__ == "__main__":
    print(get_route("5807"))
    print(get_route_day("5807", "2026-10-21"))
    print(get_route_day("5807", "2020-01-01"))   # no data -> None
    print(get_home())
    print(get_leaderboard())
    print(get_stop("2345"))                      # swap in a real stop id from stops.txt
    print(get_stop("0"))                         # not a stop -> None