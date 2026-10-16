from datetime import datetime
from zoneinfo import ZoneInfo

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