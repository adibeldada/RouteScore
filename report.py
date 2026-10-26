"""
report.py

Reads the stats table and prints the findings. Read-only, never writes.

Prints: all of Hamilton on-time %, the worst and best 5 main routes
(10,000+ arrivals), and King / Delaware hour by hour.

Run from my laptop: python report.py
"""

import boto3
from explore_static import load_routes, load_stops

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("RouteScoreStack-StatsTableV3CD71D0CC-FCBS2KYLLJX3")

# Lookups from the static schedule: id -> name
routes = load_routes("data/routes.txt")   # "5780" -> "02 BARTON"
stops = load_stops("data/stops.txt")      # "2345" -> "KING at JAMES"

MIN_ROUTE_ARRIVALS = 10000                # leaderboard only counts main routes (skips tiny/special services)
FOCUS_ROUTES = ["ROUTE#5807", "ROUTE#5783"]   # 01 KING, 05 DELAWARE: show these hour by hour


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


def hour_label(sk):
    """'HOUR#17' -> '5pm', 'HOUR#00' -> '12am'."""
    hour = int(sk.replace("HOUR#", ""))
    suffix = "am" if hour < 12 else "pm"
    return f"{hour % 12 or 12}{suffix}"


def pct(part, total):
    """Percent, safe if total is 0."""
    return part / total * 100 if total else 0


def calculate_pct(table):
    """Print system-wide on-time %, the route leaderboard, and King/Delaware by hour. 
    takes in DynamoDB table that looks like: 
    pk	        sk	early	on_time	late	total
    ROUTE#5828	ALL	11,200	83,450	18,417	113,067"""

    response = table.scan()          # SELECT * FROM stats -> {"Items": [row, row, ...], "Count": N, ...}
    rows = response["Items"]         # just the rows: [{"pk": "ROUTE#5828", "sk": "ALL", "early": 11200, ...}, ...]
    print(f"{len(rows)} rows\n")

    system = {"early": 0, "on_time": 0, "late": 0, "total": 0}   # all of Hamilton combined
    results = []                                       # route leaderboard (one dict per route)
    hourly = {}
    for pk in FOCUS_ROUTES:
        hourly[pk]= []

    for row in rows:
        pk, sk = row["pk"], row["sk"]
        early = int(row["early"])                      # DynamoDB gives Decimal -> int
        on_time = int(row["on_time"])
        late = int(row["late"])
        total = int(row["total"])

        # 1) System-wide: add up every route's overall row (all routes, no size filter)
        if pk.startswith("ROUTE#") and sk == "ALL":
            system["early"] += early
            system["on_time"] += on_time
            system["late"] += late
            system["total"] += total

            # 2) Leaderboard: only main routes
            if total >= MIN_ROUTE_ARRIVALS:
                results.append({
                    "name": label(pk, sk),
                    "early": pct(early, total),
                    "on_time": pct(on_time, total),
                    "late": pct(late, total),
                    "total": total,
                })

        # 3) Hour-by-hour rows for the focus routes
        if pk in FOCUS_ROUTES and sk.startswith("HOUR#"):
            hourly[pk].append({
                "sk": sk,
                "on_time": pct(on_time, total),
                "late": pct(late, total),
                "early": pct(early, total),
                "total": total,
            })

    # --- System-wide ---
    t = system["total"]
    print("All of Hamilton:")
    print(f"  on time {pct(system['on_time'], t):.1f}% | late {pct(system['late'], t):.1f}% | early {pct(system['early'], t):.1f}% ({t} arrivals)\n")

    # --- Leaderboard ---
    results.sort(key=lambda r: r["on_time"])           # worst -> best

    print(f"Worst 5 routes (least on time, {MIN_ROUTE_ARRIVALS}+ arrivals):")
    for r in results[:5]:
        print(f"  {r['name']}: on time {r['on_time']:.1f}% | late {r['late']:.1f}% | early {r['early']:.1f}% ({r['total']} arrivals)")

    print(f"\nBest 5 routes (most on time, {MIN_ROUTE_ARRIVALS}+ arrivals):")
    for r in reversed(results[-5:]):
        print(f"  {r['name']}: on time {r['on_time']:.1f}% | late {r['late']:.1f}% | early {r['early']:.1f}% ({r['total']} arrivals)")

    # --- Focus routes by hour of day ---
    for pk in FOCUS_ROUTES:
        name = routes.get(pk.replace("ROUTE#", ""), pk)
        print(f"\n{name} by hour (Toronto time):")
        for h in sorted(hourly[pk], key=lambda r: r["sk"]):     # HOUR#05, HOUR#06, ... in order
            if h["total"] < 200:                               # skip near-empty overnight hours
                continue
            print(f"  {hour_label(h['sk']):>4}: on time {h['on_time']:.1f}% | late {h['late']:.1f}% | early {h['early']:.1f}% ({h['total']} arrivals)")


if __name__ == "__main__":
    calculate_pct(table)