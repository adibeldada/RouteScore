"""
explore_feed.py
Playground script for exploring Hamilton's live HSR GTFS-Realtime feed.
Downloads the trip updates feed, decodes it, and prints:
  - per-stop arrival offsets (how early/late) for the first trip
  - a summary of the first 5 trips
  - basic info about the feed itself
"""

import requests                                   # for downloading the feed over HTTP
from google.transit import gtfs_realtime_pb2      # decodes GTFS-Realtime (protobuf) data

# City of Hamilton's live trip updates feed (binary protobuf, not JSON)
url = "https://opendata.hamilton.ca/GTFS-RT/GTFS_TripUpdates.pb"

# Download the feed
response = requests.get(url)

# Create an empty FeedMessage, then fill it with the downloaded bytes.
# ParseFromString changes feed_message in place (no need to assign the result).
feed_message = gtfs_realtime_pb2.FeedMessage()
feed_message.ParseFromString(response.content)

# --- Offsets for the first trip ---
# Loop over every upcoming stop of the first trip in the feed.
# Each stop has arrival.time (predicted, or actual if already passed)
# and arrival.scheduled_time (when it's supposed to arrive), both in Unix seconds.
for entity in feed_message.entity[:3]:
    route = entity.trip_update.trip.route_id
    trip_id = entity.trip_update.trip.trip_id
    print(f"\nRoute {route} | Trip {trip_id}")

    for stop in entity.trip_update.stop_time_update:
        arrival_time = stop.arrival.time
        scheduled_time = stop.arrival.scheduled_time
        offset = arrival_time - scheduled_time    # positive = late, negative = early (seconds)

        if offset < -120:
            early_late = "early"
        elif offset > 300:
            early_late = "late"
        else:
            early_late = "on time"

        print(f"  Stop {stop.stop_id} (seq {stop.stop_sequence}): offset {offset} s -> {early_late}")

    
# --- Summary of the first 5 trips ---
i = 1
for entity in feed_message.entity[:5] :
    route = entity.trip_update.trip.route_id      # internal route ID, not the public route number
    trip_id = entity.id                           # entity ID (same as trip_id in Hamilton's feed)
    upcoming_stops = entity.trip_update.stop_time_update   # list of stops not yet dropped off
    print(f"{i}: Route ID: {route} | Trip ID: {trip_id} | Upcoming stops: {len(upcoming_stops)}")
    i += 1

# --- Feed info ---
print(f"File size: {len(response.content)} bytes")
print(f"Status code: {response.status_code}")     # 200 = success
print(f"Trips in feed: {len(feed_message.entity)}")
print(f"Feed timestamp: {feed_message.header.timestamp}")   # when the feed was made (Unix seconds)