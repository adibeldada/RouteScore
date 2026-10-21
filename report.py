import boto3
from explore_static import load_routes
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("RouteScoreStack-StatsTable8BDA1AC3-1HJAECBVPCC5L")

def calculate_pct(table):
    response = table.scan()
    for row in response["Items"]:
        total = int(row["total"])
        early = int(row["early"])
        late = int(row["late"])
        on_time = int(row["on_time"])
        pct_early = early/total * 100 
        pct_late = late/total * 100 
        pct_on_time = on_time/total * 100
        print(f"{row['pk']} {row['sk']}: early {pct_early:.1f}% | on time {pct_on_time:.1f}% | late {pct_late:.1f}%")


if __name__ == "__main__":
    calculate_pct(table)