from datetime import datetime
from zoneinfo import ZoneInfo

import boto3
dynamodb = boto3.resource("dynamodb")

def aggregate(final):
    """Count arrivals into scoreboard rows: (pk, sk) -> {early, on_time, late, total}."""
    totals = {}

    for arrival in final:
        # Unix seconds -> Toronto time (used by the hour and day keys)
        when = datetime.fromtimestamp(arrival["scheduled_time"], ZoneInfo("America/Toronto"))

        route_all = ("ROUTE#" + arrival["route_id"], "ALL")                              # route overall
        route_hour = ("ROUTE#" + arrival["route_id"], "HOUR#" + when.strftime("%H"))     # route at that hour
        stop_all = ("STOP#" + arrival["stop_id"], "ALL")                                 # stop overall
        day_route = ("DAY#" + when.strftime("%Y-%m-%d"), "ROUTE#" + arrival["route_id"]) # route on that day

        # "on time" -> "on_time" (the counter names can't have spaces)
        status = arrival["status"].replace(" ", "_")

        # This one arrival adds +1 to all 4 rows it belongs to
        for key in [route_all, route_hour, stop_all, day_route]:
            if key not in totals:                                   # first time seeing this row -> start at zero
                totals[key] = {"early": 0, "on_time": 0, "late": 0, "total": 0}
            totals[key][status] += 1                                # +1 early / on_time / late
            totals[key]["total"] += 1                               # +1 total

    return totals

def save_totals(table_name, totals):
    """Add this hour's counts onto the running totals in DynamoDB (one update_item per row)."""
    # table_name = which DynamoDB table (from the TABLE_NAME env var, set by CDK)
    # totals = the dict from aggregate: (pk, sk) -> {early, on_time, late, total}
    table = dynamodb.Table(table_name)

    for (pk, sk), counts in totals.items():          # unpack the tuple key, same trick as save_arrivals
        table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression="ADD early :e, on_time :o, late :l, #t :t",   # total -> #t
            ExpressionAttributeNames={"#t": "total"},                       # new: #t means the "total" column
            ExpressionAttributeValues={
                ":e": counts["early"],
                ":o": counts["on_time"],
                ":l": counts["late"],
                ":t": counts["total"],
            },
        )
        
    print(f"Added {len(totals)} rows to {table_name}")

if __name__ == "__main__":
    records = [
        {"trip_id": "3324573", "stop_sequence": 14, "route_id": "5780", "stop_id": "2345", "time": 1760551920, "scheduled_time": 1760551680, "offset": 240, "status": "on time"},
        {"trip_id": "3324573", "stop_sequence": 15, "route_id": "5780", "stop_id": "2346", "time": 1760552400, "scheduled_time": 1760551800, "offset": 600, "status": "late"},
        {"trip_id": "3324999", "stop_sequence": 3,  "route_id": "5828", "stop_id": "1100", "time": 1760551320, "scheduled_time": 1760551500, "offset": -180, "status": "early"},
    ]

    totals = aggregate(records)
    for key, counts in totals.items():
        print(key, counts)