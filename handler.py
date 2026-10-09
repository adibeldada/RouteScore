"""
handler.py
AWS Lambda entry point for RouteScore.
Fetches Hamilton's live HSR trip updates feed.
"""

import requests
from google.transit import gtfs_realtime_pb2

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
    print(f"Trips in feed: {len(feed.entity)}")


# Only runs when executed directly (python handler.py), not when AWS imports the file
if __name__ == "__main__":
    lambda_handler(None, None)