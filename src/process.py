"""
process.py
Turns saved feed snapshots into final arrival records (one per bus per stop).
"""

import gzip                                       # decompress the saved snapshots
import json                                       # save results as JSON Lines
import os                                         # list the files in a folder

import boto3                                      # AWS SDK for Python (talk to S3)
from google.transit import gtfs_realtime_pb2      # decode GTFS-Realtime (protobuf) data

# Created once when the file loads, then reused (faster on warm Lambda runs)
s3 = boto3.client("s3")


def parse_snapshot(data):
    """Decompress + parse one snapshot's bytes into a FeedMessage."""
    decompressed_bytes = gzip.decompress(data)

    feed_message = gtfs_realtime_pb2.FeedMessage()
    feed_message.ParseFromString(decompressed_bytes)
    return feed_message


def read_snapshot(path):
    """Read one saved .pb.gz snapshot from a local file and return it as a FeedMessage."""
    with open(path, "rb") as f:
        data = f.read()

    return parse_snapshot(data)


def load_feeds_from_s3(bucket_name, prefix):
    """Download every snapshot under a prefix (oldest first) and return them as feeds."""
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    keys = []
    for item in response.get("Contents", []):    # each item = one file's info
        keys.append(item["Key"])                  # we only need its name (key)
    keys.sort()                                    # oldest first (keys are time-named)

    feeds = []
    for key in keys:
        obj = s3.get_object(Bucket=bucket_name, Key=key)
        data = obj["Body"].read()                  # the file's bytes, like f.read()
        feeds.append(parse_snapshot(data))

    return feeds


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


def summarize(final):
    """Print how many arrivals were early / on time / late."""
    early_counter = 0
    on_time_counter = 0
    late_counter = 0

    for value in final.values():
        if value["status"] == "early":
            early_counter += 1
        elif value["status"] == "on time":
            on_time_counter += 1
        elif value["status"] == "late":
            late_counter += 1

    total = len(final)
    print(f"\nResults ({total} arrivals):")
    print(f"early:   {early_counter} ({early_counter / total * 100:.1f}%)")
    print(f"on time: {on_time_counter} ({on_time_counter / total * 100:.1f}%)")
    print(f"late:    {late_counter} ({late_counter / total * 100:.1f}%)")


def save_arrivals(bucket_name, key, final):
    """Save final arrivals to S3 as gzipped JSON Lines (one arrival per line)."""
    lines = []
    for (trip_id, stop_sequence), value in final.items():   # unpack the tuple key right in the loop
        record = {
            "trip_id": trip_id,
            "stop_sequence": stop_sequence,
            "route_id": value["route_id"],
            "stop_id": value["stop_id"],
            "time": value["time"],
            "scheduled_time": value["scheduled_time"],
            "offset": value["offset"],
            "status": value["status"],
        }
        lines.append(json.dumps(record))                    # dict -> one JSON string

    body = "\n".join(lines).encode("utf-8")                 # one string -> bytes
    compressed = gzip.compress(body)

    s3.put_object(Bucket=bucket_name, Key=key, Body=compressed)
    print(f"Saved {len(lines)} arrivals to {key}")


# Only runs when executed directly, not when imported (e.g. by the Lambda later)
if __name__ == "__main__":
    BUCKET = "routescorestack-rawfeedbucket504cf208-nsj9oprvyysm"

    # --- Test 1: local snapshots ---
    snapshot_names = sorted(os.listdir("snapshots"))
    feeds = []
    for snapshot_name in snapshot_names:
        feeds.append(read_snapshot(os.path.join("snapshots", snapshot_name)))
    print(f"Loaded {len(feeds)} local snapshots")

    final = find_final_arrivals(feeds)
    print(f"Final arrivals: {len(final)}")
    summarize(final)

    # --- Test 2: the same kind of data, straight from S3 (10 files: 21:00-21:09 UTC) ---
    s3_feeds = load_feeds_from_s3(BUCKET, "raw/2026/10/09/210")
    print(f"\nLoaded {len(s3_feeds)} snapshots from S3")

    s3_final = find_final_arrivals(s3_feeds)
    print(f"Final arrivals: {len(s3_final)}")
    summarize(s3_final)

    # --- Test 3: save the S3 results back to S3 as JSON Lines ---
    save_arrivals(BUCKET, "arrivals/test.jsonl.gz", s3_final)