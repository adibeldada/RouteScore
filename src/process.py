"""
process.py
Turns saved feed snapshots into final arrival records (one per bus per stop).
"""

import gzip                                       # decompress the saved snapshots
import os                                         # list the files in a folder
import boto3                                      # AWS SDK for Python (talk to S3)

from google.transit import gtfs_realtime_pb2      # decode GTFS-Realtime (protobuf) data


def read_snapshot(path):
    """Read one saved .pb.gz snapshot and return it as a FeedMessage."""
    with open(path, "rb") as f:
        data = f.read()

    decompressed_bytes = gzip.decompress(data)

    feed_message = gtfs_realtime_pb2.FeedMessage()
    feed_message.ParseFromString(decompressed_bytes)
    return feed_message


def classify(offset):
    """City's on-time rule: more than 2 min early = early, more than 5 min late = late."""
    if offset < -120:
        return "early"
    elif offset > 300:
        return "late"
    else:
        return "on time"


def find_final_arrivals(feeds):
    """Go through feeds oldest-first, keep the latest prediction for each (trip, stop),
    then keep only stops the bus has passed (gone from the last snapshot)."""
    latest = {}

    for feed in feeds:                                        # each minute's snapshot
        for entity in feed.entity:                            # each trip in that snapshot
            trip_id = entity.trip_update.trip.trip_id
            route_id = entity.trip_update.trip.route_id
            if route_id == "":                                # skip duplicate trips
                continue

            for stop in entity.trip_update.stop_time_update:  # each upcoming stop of that trip
                key = (trip_id, stop.stop_sequence)
                value = {
                    "route_id": route_id,
                    "stop_id": stop.stop_id,
                    "time": stop.arrival.time,
                    "scheduled_time": stop.arrival.scheduled_time,
                }
                latest[key] = value                           # newer overwrites older

    # Stops still in the last snapshot = bus hasn't reached them yet
    still_upcoming = set()
    for entity in feeds[-1].entity:
        trip_id = entity.trip_update.trip.trip_id
        for stop in entity.trip_update.stop_time_update:
            still_upcoming.add((trip_id, stop.stop_sequence))

    # Keep only the stops the bus actually passed, and label them
    results = {}
    for key, value in latest.items():
        if key not in still_upcoming:
            value["offset"] = value["time"] - value["scheduled_time"]   # positive = late
            value["status"] = classify(value["offset"])
            results[key] = value

    return results


# Only runs when executed directly, not when imported (e.g. by the Lambda later)
if __name__ == "__main__":
    # Load all snapshots, oldest first (file names are times, so sorting = time order)
    snapshot_names = sorted(os.listdir("snapshots"))
    feeds = []
    for snapshot_name in snapshot_names:
        feeds.append(read_snapshot(os.path.join("snapshots", snapshot_name)))
    print(f"Loaded {len(feeds)} snapshots")

    final = find_final_arrivals(feeds)
    print(f"Final arrivals: {len(final)}")

    # Peek at the first 5 records
    for key, value in list(final.items())[:5]:
        print(key, value)

    early_counter = 0
    on_time_counter = 0
    late_counter = 0

    for values in final.values():
        if (values["status"] == "early"):
            early_counter += 1
        if (values["status"] == "on time"):
            on_time_counter += 1
        if (values["status"] == "late"):
            late_counter += 1
    
    total = len(final)
    print(f"\nResults ({total} arrivals):")
    print(f"early:   {early_counter} ({early_counter / total * 100:.1f}%)")
    print(f"on time: {on_time_counter} ({on_time_counter / total * 100:.1f}%)")
    print(f"late:    {late_counter} ({late_counter / total * 100:.1f}%)")
            