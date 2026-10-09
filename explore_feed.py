"""
explore_feed.py
Playground script for exploring Hamilton's live HSR GTFS-Realtime feed.
Downloads the trip updates feed, decodes it, and prints:
  - per-stop arrival offsets (early / on time / late) for the first 3 trips,
    with real route and stop names from the static schedule
  - the planned time from stop_times.txt next to the feed's scheduled time
  - a summary of the first 5 trips
  - basic info about the feed itself
"""

from datetime import datetime                     # turn Unix seconds into a readable time

import requests                                   # for downloading the feed over HTTP
from google.transit import gtfs_realtime_pb2      # decodes GTFS-Realtime (protobuf) data
from explore_static import load_routes, load_stops, load_stop_times   # my static schedule lookups

# City of Hamilton's live trip updates feed (binary protobuf, not JSON)
url = "https://opendata.hamilton.ca/GTFS-RT/GTFS_TripUpdates.pb"

# Download the feed
response = requests.get(url)

# Create an empty FeedMessage, then fill it with the downloaded bytes.
feed_message = gtfs_realtime_pb2.FeedMessage()
feed_message.ParseFromString(response.content)

# Load the lookups once: route_id -> "02 BARTON", stop_id -> "MELVIN at ADAIR",
# (trip_id, stop_sequence) -> "4:30:00"
routes = load_routes("data/routes.txt")
stops = load_stops("data/stops.txt")
stop_times = load_stop_times("data/stop_times.txt")   # ~633,000 rows, takes a few seconds

# --- Offsets for the first 3 trips ---
# arrival.time = predicted (or actual if just passed), arrival.scheduled_time = planned.
# Both are Unix seconds, so offset = how many seconds late (+) or early (-).
for entity in feed_message.entity[:3]:
    route = entity.trip_update.trip.route_id
    route_name = routes.get(route, "Unknown route")   # .get: blank IDs on duplicate trips won't crash
    trip_id = entity.trip_update.trip.trip_id
    print(f"\nRoute {route_name} | Trip {trip_id}")

    for stop in entity.trip_update.stop_time_update:
        arrival_time = stop.arrival.time
        scheduled_time = stop.arrival.scheduled_time
        offset = arrival_time - scheduled_time        # positive = late, negative = early (seconds)
        stop_name = stops.get(stop.stop_id, "Unknown stop")

        # Planned time from the static schedule, looked up by (trip, stop number)
        static_time = stop_times.get((trip_id, stop.stop_sequence), "not in schedule")
        # The feed's scheduled_time as a clock time on this computer (Toronto), to compare
        feed_time = datetime.fromtimestamp(scheduled_time).strftime("%H:%M:%S")

        # City's on-time rule: no more than 2 min early or 5 min late
        if offset < -120:
            early_late = "early"
        elif offset > 300:
            early_late = "late"
        else:
            early_late = "on time"

        print(f"  Stop {stop_name} (seq {stop.stop_sequence}): "
              f"schedule {static_time} | feed {feed_time} | offset {offset} s -> {early_late}")


# --- Summary of the first 5 trips ---
for i, entity in enumerate(feed_message.entity[:5], start=1):   # enumerate = loop with a counter
    route = entity.trip_update.trip.route_id
    route_name = routes.get(route, "Unknown route")
    trip_id = entity.trip_update.trip.trip_id
    upcoming_stops = entity.trip_update.stop_time_update        # stops not yet dropped off
    print(f"{i}: Route {route_name} | Trip {trip_id} | Upcoming stops: {len(upcoming_stops)}")

# --- Feed info ---
print(f"File size: {len(response.content)} bytes")
print(f"Status code: {response.status_code}")                    # 200 = success
print(f"Trips in feed: {len(feed_message.entity)}")
print(f"Feed timestamp: {feed_message.header.timestamp}")        # when the feed was made (Unix seconds)