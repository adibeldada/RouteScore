import gzip                                    # unzip each arrivals file
import json                                    # turn each line into a dict

import boto3                                   # talk to S3
from src.stats import aggregate, save_totals   # count + save to DynamoDB

BUCKET = "routescorestack-rawfeedbucket504cf208-nsj9oprvyysm"
TABLE_NAME = "RouteScoreStack-StatsTableV2132B31BE-24JNAZIFB7U9"
CUTOFF = "arrivals/2026/10/25/22"

s3 = boto3.client("s3")    # the connection

def list_arrival_files():
    """Return the names of every arrivals file before CUTOFF, oldest first.

    Returns a list of strings (S3 keys), e.g.:
        ["arrivals/2026/10/15/18.jsonl.gz",
         "arrivals/2026/10/15/19.jsonl.gz",
         ...
         "arrivals/2026/10/25/21.jsonl.gz"]     # ~198 names
    """
    # List every file whose name starts with "arrivals/" (names + info only, no contents).
    # Returns a dict, e.g.:
    #   {"KeyCount": 199,
    #    "Contents": [{"Key": "arrivals/2026/10/15/18.jsonl.gz", "Size": 157217, ...},
    #                 {"Key": "arrivals/2026/10/15/19.jsonl.gz", "Size": 180630, ...}, ...]}
    # Only "Key" is needed. Max 1,000 files per call (I have ~200).
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix="arrivals/")

    keys = []
    for item in response["Contents"]:          # each item = one file's info
        key = item["Key"]                      # just its name
        if key < CUTOFF:                       # only hours the Lambda didn't already count
            keys.append(key)

    keys.sort()                                # oldest first (names are time-based)
    return keys                                # list of file names (strings), not the files themselves

def read_arrivals(key):
    """Download one arrivals file and return its arrivals.

    key = one file name, e.g. "arrivals/2026/10/15/18.jsonl.gz"

    Returns a list of dicts (one per arrival), e.g.:
        [{"trip_id": "3324573", "stop_sequence": 14, "route_id": "5780", "stop_id": "2345",
          "time": 1760551920, "scheduled_time": 1760551680, "offset": 240, "status": "on time"},
         ...]                                   # ~10,000 for a busy hour, 0 for 3-4am
    """
    # Download one file by its name (key).
    # Returns a dict: {"Body": <StreamingBody>, "ContentLength": 157217, "LastModified": ..., ...}
    obj = s3.get_object(Bucket=BUCKET, Key=key)

    data = obj["Body"].read()            # the file's bytes, still gzipped: b'\x1f\x8b...'
    unzipped = gzip.decompress(data)     # real bytes: b'{"trip_id": ...}\n{"trip_id": ...}'
    text = unzipped.decode("utf-8")      # bytes -> string: '{"trip_id": ...}\n{"trip_id": ...}'
    lines = text.split("\n")             # one string per arrival: ['{"trip_id": ...}', ...]

    arrivals = []
    for line in lines:
        if not line:                     # empty file (3-4am) or blank line -> nothing to read
            continue
        arrivals.append(json.loads(line))   # one JSON line -> one dict

    return arrivals                      # list of arrival dicts, ready for aggregate()

def run_backfill(keys):
    """Read each arrivals file, count it, and add it to the DynamoDB table.

    keys = list of file names from list_arrival_files()
    Prints progress per file and the total number of arrivals at the end.
    """
    total_arrivals = 0                              # running count across all files

    for key in keys:
        arrivals = read_arrivals(key)               # one hour's arrivals: list of dicts
        totals = aggregate(arrivals)                # count them: (pk, sk) -> {early, on_time, late, total}
        save_totals(TABLE_NAME, totals)             # ADD those counts into the table

        total_arrivals += len(arrivals)             # keep the overall count
        print(f"{key}: {len(arrivals)} arrivals")   # progress, one line per file

    print(f"\nDone: {len(keys)} files, {total_arrivals} arrivals")


if __name__ == "__main__":
    keys = list_arrival_files()
    print(f"{len(keys)} files to backfill: {keys[0]} -> {keys[-1]}\n")

    # The first 2 files were already added in the test run, so skip them (no double counting).
    # Run this ONCE.
    run_backfill(keys[2:])