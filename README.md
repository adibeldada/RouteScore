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
