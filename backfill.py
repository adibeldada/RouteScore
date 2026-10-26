"""
backfill.py

Rebuilds the DynamoDB stats table from every saved arrivals/ file in S3.

Counts everything in memory first, then SETs each row to its exact total,
so it's safe to rerun (no double counting). Uses aggregate from src/stats.py.
Only runs between :10 and :55 so it never overlaps the hourly Lambda.

Run from my laptop: python backfill.py
"""


import gzip                                    # unzip each arrivals file
import json                                    # turn each line into a dict
from concurrent.futures import ThreadPoolExecutor   # write many rows at once
from datetime import datetime                  # safety check on the time

import boto3                                   # talk to S3 + DynamoDB
from src.stats import aggregate                # count arrivals into scoreboard rows

BUCKET = "routescorestack-rawfeedbucket504cf208-nsj9oprvyysm"
TABLE_NAME = "RouteScoreStack-StatsTableV3CD71D0CC-FCBS2KYLLJX3"

s3 = boto3.client("s3")
dynamodb = boto3.client("dynamodb")            # ONE client shared by all threads (clients are thread-safe)


def list_arrival_files():
    """Return the names of EVERY arrivals file, oldest first.

    Returns a list of strings, e.g. ["arrivals/2026/10/15/18.jsonl.gz", ..., "arrivals/2026/10/26/01.jsonl.gz"]
    """
    # List every file whose name starts with "arrivals/" (names + info only, no contents).
    # Returns a dict: {"KeyCount": 244, "Contents": [{"Key": "arrivals/...", "Size": ...}, ...]}
    # Max 1,000 files per call (I have ~244).
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix="arrivals/")

    keys = []
    for item in response["Contents"]:          # each item = one file's info
        keys.append(item["Key"])               # just its name

    keys.sort()                                # oldest first (names are time-based)
    return keys


def read_arrivals(key):
    """Download one arrivals file and return its arrivals (list of dicts, one per arrival)."""
    obj = s3.get_object(Bucket=BUCKET, Key=key)   # {"Body": <StreamingBody>, "ContentLength": ..., ...}

    data = obj["Body"].read()            # the file's bytes, still gzipped
    unzipped = gzip.decompress(data)     # real bytes
    text = unzipped.decode("utf-8")      # bytes -> string
    lines = text.split("\n")             # one string per arrival

    arrivals = []
    for line in lines:
        if not line:                     # empty file (3-4am) or blank line
            continue
        arrivals.append(json.loads(line))   # one JSON line -> one dict
    return arrivals


def merge(all_totals, totals):
    """Add one hour's totals into the grand totals (both: (pk, sk) -> {early, on_time, late, total})."""
    for key, counts in totals.items():
        if key not in all_totals:                       # first time seeing this row
            all_totals[key] = {"early": 0, "on_time": 0, "late": 0, "total": 0}
        for field in ["early", "on_time", "late", "total"]:
            all_totals[key][field] += counts[field]     # add this hour's numbers on top


def set_row(item):
    """Write ONE row's final totals. SET overwrites, so rerunning is safe (no double counting)."""
    (pk, sk), counts = item
    # The low-level client needs types: "S" = string, "N" = number (sent as text)
    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"pk": {"S": pk}, "sk": {"S": sk}},
        UpdateExpression="SET early = :e, on_time = :o, late = :l, #t = :t",
        ExpressionAttributeNames={"#t": "total"},       # "total" is a reserved word
        ExpressionAttributeValues={
            ":e": {"N": str(counts["early"])},
            ":o": {"N": str(counts["on_time"])},
            ":l": {"N": str(counts["late"])},
            ":t": {"N": str(counts["total"])},
        },
    )


def rebuild():
    """Recount every arrivals file from scratch, then write the correct totals to the table."""
    # Safety: the hourly Lambda writes around :05. Don't overlap with it.
    minute = datetime.now().minute
    if minute < 10 or minute > 55:
        print(f"It's :{minute:02d} - run between :10 and :55 so the hourly Lambda doesn't overlap.")
        return

    keys = list_arrival_files()
    print(f"{len(keys)} files: {keys[0]} -> {keys[-1]}\n")

    # Step 1: count everything in memory (nothing written yet)
    all_totals = {}
    total_arrivals = 0
    for key in keys:
        arrivals = read_arrivals(key)
        merge(all_totals, aggregate(arrivals))
        total_arrivals += len(arrivals)
        print(f"{key}: {len(arrivals)} arrivals")

    print(f"\nCounted {total_arrivals} arrivals into {len(all_totals)} rows. Writing...")

    # Step 2: write each row once, 16 at a time
    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(set_row, all_totals.items()))     # list() waits for all, and re-raises any error

    print(f"Done: {len(keys)} files, {total_arrivals} arrivals, {len(all_totals)} rows written")


if __name__ == "__main__":
    rebuild()