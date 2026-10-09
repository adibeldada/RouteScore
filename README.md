Status: IN PROGRESS

# RouteScore

## Overview
RouteScore tracks how reliable Hamilton's HSR buses really are. Every minute, it collects live bus data from the City of Hamilton and compares where buses actually are against where the schedule says they should be. Over time, it builds a reliability history for every route, stop, and hour of the day, so riders can see things like "Route 51 is late 38% of the time between 8 and 9am." It also catches "ghost buses," trips that were scheduled but never showed up, and alerts riders when their usual bus is running badly.

## Features

### Core (in progress)
- Collect live HSR bus data every minute
- Compare actual vs. scheduled arrival times using the city's on-time definition (no more than 2 min early or 5 min late)
- Reliability stats by route, stop, and hour of day
- Ghost bus detection: scheduled trips that never appeared
- Public dashboard showing the most and least reliable routes
- Subscribe to a route or stop and get email alerts when it's running late or cancelled

### Planned
- Delay prediction using historical data
- Weekly reliability report by email
- Weather impact on delays
- Live map of buses
- Comparison with the city's official on-time numbers

## Tech Stack
- Language: Python
- Compute: AWS Lambda
- Scheduling: Amazon EventBridge
- Messaging: Amazon SQS
- Database: Amazon DynamoDB (live data and stats), Amazon S3 (raw data archive)
- Alerts: Amazon SNS
- API: Amazon API Gateway
- Frontend: HTML/JavaScript, hosted on S3 + CloudFront
- Infrastructure as Code: AWS CDK (Python)
- Testing: pytest, moto (mocked AWS services)
- CI/CD: GitHub Actions

## Data Source
Contains information licensed under the Open Government Licence – City of Hamilton. Uses the HSR GTFS schedule and GTFS-Realtime feeds.
Not affiliated with the City of Hamilton or the HSR.

## Roadmap

### ✅ v0.1: Live data collection
- [x] Fetch live HSR trip updates every minute (Lambda + EventBridge)
- [x] Save raw feed snapshots to S3
- [x] Load the static HSR schedule (routes, stops, scheduled times)

### v0.2: Delay tracking (in progress)
- [ ] Match live trips to their scheduled trips
- [ ] Calculate how late each bus is at each stop
- [ ] Classify arrivals as early, on time, or late (city definition: max 2 min early, 5 min late)
- [ ] Store results in DynamoDB

### v0.3: Reliability stats
- [ ] On-time % per route
- [ ] On-time % per stop
- [ ] On-time % by hour of day (e.g. rush hour vs. evening)
- [ ] Daily summaries so stats build up over time

### v0.4: Public dashboard
- [ ] Route leaderboard: most and least reliable routes
- [ ] Route page with hour-by-hour reliability chart
- [ ] Stop lookup: how reliable is my stop?

### v0.5: Quality
- [ ] Unit tests (pytest) for delay and stats logic
- [ ] AWS tests with mocked services (moto)
- [ ] GitHub Actions CI
- [ ] Automatic deployment with AWS CDK

### v0.6: Ghost buses
- [ ] Detect scheduled trips that never appeared
- [ ] Ghost bus count per route on the dashboard

### v0.7: Alerts
- [ ] Subscribe to a route or stop by email
- [ ] Get alerted when your bus is running late or cancelled (SNS)

### v0.8: Fault tolerance
- [ ] Queue between fetching and processing (SQS), so one failing doesn't break the other
- [ ] Retry failed processing and capture bad data (dead-letter queue)
- [ ] Detect feed outages and mark gaps clearly instead of skewing stats

### v0.9: Rider experience
- [ ] Mobile-friendly dashboard
- [ ] Live map of buses
- [ ] HTTPS and faster loading (CloudFront)
- [ ] Compare with the city's official on-time numbers

### v1.0: Stable release
- [ ] Runs for a full month without manual fixes
- [ ] Monitoring: get notified if data collection stops (CloudWatch alarms)
- [ ] Architecture diagram and screenshots in README
- [ ] Runs within AWS free usage limits

### Future ideas
- [ ] Delay prediction from historical data
- [ ] Weather impact on delays
- [ ] Weekly reliability report by email