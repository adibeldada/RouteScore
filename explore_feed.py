import requests

url = "https://opendata.hamilton.ca/GTFS-RT/GTFS_TripUpdates.pb"

response = requests.get(url)

print(len(response.content))