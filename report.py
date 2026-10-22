import boto3
from explore_static import load_routes, load_stops

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("RouteScoreStack-StatsTable8BDA1AC3-1HJAECBVPCC5L")

# Lookups from the static schedule: id -> name
routes = load_routes("data/routes.txt")   # "5780" -> "02 BARTON"
stops = load_stops("data/stops.txt")      # "2345" -> "KING at JAMES"


def label(pk, sk):
    """Turn a row's keys into something readable."""
    if pk.startswith("ROUTE#"):                        # ROUTE#5780 / ALL or HOUR#17
        route_id = pk.replace("ROUTE#", "")
        name = routes.get(route_id, "Unknown route " + route_id)
        return f"{name} / {sk}"

    elif pk.startswith("STOP#"):                       # STOP#2345 / ALL
        stop_id = pk.replace("STOP#", "")
        name = stops.get(stop_id, "Unknown stop " + stop_id)
        return f"Stop: {name}"

    elif pk.startswith("DAY#"):                        # DAY#2026-10-21 / ROUTE#5780 (route is in sk)
        day = pk.replace("DAY#", "")
        route_id = sk.replace("ROUTE#", "")
        name = routes.get(route_id, "Unknown route " + route_id)
        return f"{day} / {name}"

    return f"{pk} / {sk}"                              # anything else: show as is


def calculate_pct(table):
    """Read every row and print its early / on time / late %."""
    response = table.scan()
    rows = response["Items"]
    print(f"{len(rows)} rows\n")

    for row in rows:
        total = int(row["total"])                      # DynamoDB gives Decimal -> int
        early = int(row["early"])
        on_time = int(row["on_time"])
        late = int(row["late"])

        pct_early = early / total * 100
        pct_on_time = on_time / total * 100
        pct_late = late / total * 100

        print(f"{label(row['pk'], row['sk'])}: early {pct_early:.1f}% | on time {pct_on_time:.1f}% | late {pct_late:.1f}% ({total} arrivals)")


if __name__ == "__main__":
    calculate_pct(table)