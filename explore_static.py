import csv


def load_routes(path):
    """Read routes.txt into a dict of route_id -> 'short long' name."""
    routes = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            route_id = row["route_id"]
            route_name = f"{row['route_short_name']} {row['route_long_name']}"
            routes[route_id] = route_name

    return routes

def load_stops(path):
    """Read stops.txt into a dict of route_id -> 'short long' name."""
    stops = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stop_id = row["stop_id"]
            stop_name = row["stop_name"]
            stops[stop_id] = stop_name

    return stops


# Only runs when executed directly, not when another file imports this one
if __name__ == "__main__":
    routes = load_routes("data/routes.txt")
    stops = load_stops("data/stops.txt")
    print(routes["5780"])   # should print: 02 BARTON
    print(stops["2203"])