# Aircraft monitor

Script for monitoring and alerting on specific aircraft types within a certain radius of a given location, using the [Flight Finder API](https://github.com/grega/flight-finder).

## Set up

Create `.env` from `.env.example` and set environment variables.

```
asdf install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

Ensure to have the [Flight Finder API](https://github.com/grega/flight-finder) running and accessible at the URL specified in the `.env` file.

Then run the flight monitor script:

```
python aircraft_monitor.py
```

## Example output

```
$ python aircraft_monitor.py
Monitoring for A400s within 100km of (xx.xxxx, xx.xxxx)...
Fetching flights from: http://0.0.0.0:7478/flights-in-radius?lat=xx.xxxx&lon=xx.xxxx&radius=100
Response status: 200
Found 23 flights in radius.

--- 2 A400(s) detected ---
🚨 LOW ALTITUDE ALERT: A400 ASLAN78 at 267m, 127.7km away, inf minutes until closest approach.
Alert thresholds not met. Skipping email.
ℹ️ A400 detected: FLTOT49 at 1219m, 43.3km away, 6 minutes until closest approach.
Alert thresholds not met. Skipping email.
---
```

Alerts will be sent via email if they meet the criteria defined in the `.env` file (eg. distance, altitude, est. time from location).
