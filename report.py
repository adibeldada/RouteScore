import boto3
from explore_static import load_routes, load_stops

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("RouteScoreStack-StatsTableV3CD71D0CC-FCBS2KYLLJX3")

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
    """Read every row, then print the 5 worst and 5 best routes by on-time %."""
    response = table.scan()
    rows = response["Items"]
    print(f"{len(rows)} rows\n")

    results = []                                       # one dict per route (overall)

    for row in rows:
        total = int(row["total"])                      # DynamoDB gives Decimal -> int
        if total < 500:                                # too few arrivals to trust the %
            continue

        early = int(row["early"])
        on_time = int(row["on_time"])
        late = int(row["late"])

        pct_early = early / total * 100
        pct_on_time = on_time / total * 100
        pct_late = late / total * 100

        # Only routes overall (ROUTE#... / ALL) go on the leaderboard
        if row["pk"].startswith("ROUTE#") and row["sk"] == "ALL":
            results.append({
                "name": label(row["pk"], row["sk"]),   # "02 BARTON / ALL" instead of "ROUTE#5780"
                "early": pct_early,
                "on_time": pct_on_time,
                "late": pct_late,
                "total": total,
            })

    # Sort worst -> best by on-time % (like ORDER BY on_time)
    results.sort(key=lambda r: r["on_time"])

    print("Worst 5 routes (least on time):")
    for r in results[:5]:                              # first 5 = lowest on-time %
        print(f"  {r['name']}: on time {r['on_time']:.1f}% | late {r['late']:.1f}% | early {r['early']:.1f}% ({r['total']} arrivals)")

    print("\nBest 5 routes (most on time):")
    for r in reversed(results[-5:]):                   # last 5 = highest; reversed so #1 prints first
        print(f"  {r['name']}: on time {r['on_time']:.1f}% | late {r['late']:.1f}% | early {r['early']:.1f}% ({r['total']} arrivals)")

if __name__ == "__main__":
    calculate_pct(table)