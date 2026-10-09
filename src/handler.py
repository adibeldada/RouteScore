"""
handler.py
AWS Lambda entry point for RouteScore.
Fetches Hamilton's live HSR trip updates feed.
"""

import gzip                                       # compress the feed before saving
import os                                         # read environment variables (BUCKET_NAME)
from datetime import datetime, timezone           # turn the Unix timestamp into a date for the filename

import boto3                                      # AWS SDK for Python (talk to S3)
import requests                                   # download the feed over HTTP
from google.transit import gtfs_realtime_pb2      # decode GTFS-Realtime (protobuf) data

# City of Hamilton's live trip updates feed (binary protobuf, not JSON)
FEED_URL = "https://opendata.hamilton.ca/GTFS-RT/GTFS_TripUpdates.pb"


def fetch_feed():
    """Download and decode the live feed. Raises an error if the request fails."""
    response = requests.get(FEED_URL, timeout=10)   # give up after 10 s if no response
    response.raise_for_status()                      # stop on 4xx/5xx instead of parsing an error page

    feed_message = gtfs_realtime_pb2.FeedMessage()
    feed_message.ParseFromString(response.content)
    return feed_message


def lambda_handler(event, context):
    """Called by AWS on each run. event/context are passed in by AWS (unused for now)."""
    feed = fetch_feed()
    save_snapshot(feed)
    print(f"Trips in feed: {len(feed.entity)}")

def save_snapshot(feed):
    """Compress the feed and upload it to S3."""
    bucket_name = os.environ.get("BUCKET_NAME")

    if bucket_name is None :
        print("BUCKET_NAME not set, skipping save")
        return
    
    raw_bytes = feed.SerializeToString()
    compressed_bytes = gzip.compress(raw_bytes)

    key = datetime.fromtimestamp(feed.header.timestamp, tz=timezone.utc).strftime("raw/%Y/%m/%d/%H%M%S.pb.gz")

    s3 = boto3.client("s3")

    s3.put_object(Bucket=bucket_name, Key=key, Body=compressed_bytes)

    print(f"Saved {key}")



# Only runs when executed directly (python handler.py), not when AWS imports the file
if __name__ == "__main__":
    lambda_handler(None, None)