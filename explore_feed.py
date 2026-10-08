import requests
from google.transit import gtfs_realtime_pb2

url = "https://opendata.hamilton.ca/GTFS-RT/GTFS_TripUpdates.pb"

response = requests.get(url)

feed_message = gtfs_realtime_pb2.FeedMessage()

feed_message.ParseFromString(response.content)

print(len(response.content))
print(response.status_code)
print(len(feed_message.entity))
print(feed_message.header.timestamp)
print(feed_message.entity[0])