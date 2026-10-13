"""
process.py
Turns saved feed snapshots into final arrival records (one per bus per stop).
"""

import gzip                                       # decompress the saved snapshots
from google.transit import gtfs_realtime_pb2      # decode GTFS-Realtime (protobuf) data

def read_snapshot(path) :
    
    with open(path, "rb") as f:
        data = f.read()

    decompressed_bytes = gzip.decompress(data)

    feed_message = gtfs_realtime_pb2.FeedMessage()
    feed_message.ParseFromString(decompressed_bytes)

    return feed_message




if __name__ == "__main__":
    feed = read_snapshot("snapshots/210028.pb.gz")
    print(len(feed.entity))
    print(feed.header.timestamp)