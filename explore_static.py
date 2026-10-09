"""
explore_static.py
Loads lookups from Hamilton's static GTFS schedule (the files in data/).
"""

import csv


def load_routes(path):
    """Read routes.txt into a dict of route_id -> 'short long' name."""
    routes = {}

    with open(path, newline="", encoding="utf-8") as f:   # newline="" = let csv handle line endings
        reader = csv.DictReader(f)                          # first line = column names
        for row in reader:
            route_id = row["route_id"]
            route_name = f"{row['route_short_name']} {row['route_long_name']}"   # e.g. "02 BARTON"
            routes[route_id] = route_name

    return routes


def load_stops(path):
    """Read stops.txt into a dict of stop_id -> stop name."""
    stops = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stop_id = row["stop_id"]
            stop_name = row["stop_name"]                    # e.g. "MELVIN at ADAIR"
            stops[stop_id] = stop_name

    return stops


def load_stop_times(path):
    """Read stop_times.txt into a dict of (trip_id, stop_sequence) -> scheduled arrival time."""
    stop_times = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Key is a tuple (pair): a scheduled time belongs to one stop of one trip
            key = (row["trip_id"], int(row["stop_sequence"]))   # int() so it matches the live feed
            stop_times[key] = row["arrival_time"].strip()        # strip() removes the leading space

    return stop_times


# Only runs when executed directly, not when another file imports this one
if __name__ == "__main__":
    routes = load_routes("data/routes.txt")
    stops = load_stops("data/stops.txt")
    stop_times = load_stop_times("data/stop_times.txt")    # ~633,000 rows, takes a few seconds

    print(routes["5780"])                  # 02 BARTON
    print(stops["2203"])                   # MELVIN at ADAIR
    print(len(stop_times))                 # 633607
    print(stop_times[("2188833", 1)])      # 4:30:00