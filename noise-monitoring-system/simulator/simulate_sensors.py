"""
Sensor Node Simulator
======================
Stands in for the physical ESP8266 + LM393 firmware described in the
project (see firmware pseudocode at the bottom of this file) so the
whole system -- ingestion, threshold evaluation, alerting, dashboard --
can be exercised end-to-end without physical hardware.

It posts realistic, slowly-drifting decibel readings to the backend's
/api/readings endpoint every few seconds, per configured sensor, and
occasionally spikes a reading above threshold so you can see alerts
fire on the dashboard.

Usage:
    python simulate_sensors.py --server http://localhost:5000

Configure SENSORS below with the sensor_code/api_key pairs created by
schema.sql (or by POST /api/sensors) for your database.
"""
import argparse
import random
import time
import datetime

import requests

# sensor_code is just for logging; api_key is what authenticates the POST.
SENSORS = [
    {"sensor_code": "SN-LR-01", "api_key": "demo-key-lr01-change-me", "baseline": 55, "spike_chance": 0.08},
    {"sensor_code": "SN-LAB-02", "api_key": "demo-key-lab02-change-me", "baseline": 50, "spike_chance": 0.05},
    {"sensor_code": "SN-LIB-03", "api_key": "demo-key-lib03-change-me", "baseline": 38, "spike_chance": 0.10},
]


def next_reading(state):
    """Random-walk the decibel value around a baseline, with occasional
    spikes, roughly mimicking real classroom noise behaviour."""
    drift = random.uniform(-1.5, 1.5)
    state["value"] = max(25.0, state["value"] + drift)

    if random.random() < state["spike_chance"]:
        state["value"] += random.uniform(10, 22)  # simulate a noisy burst

    # gently pull back toward baseline so spikes don't compound forever
    state["value"] += (state["baseline"] - state["value"]) * 0.1
    return round(state["value"], 2)


def run(server, interval):
    states = [{"value": float(s["baseline"]), **s} for s in SENSORS]

    print(f"Simulating {len(states)} sensor node(s) -> {server}/api/readings every {interval}s")
    print("Press Ctrl+C to stop.\n")

    while True:
        for s in states:
            decibel_value = next_reading(s)
            payload = {
                "decibel_value": decibel_value,
                "recorded_at": datetime.datetime.utcnow().isoformat(),
            }
            headers = {"X-Sensor-Key": s["api_key"]}
            try:
                resp = requests.post(f"{server}/api/readings", json=payload, headers=headers, timeout=5)
                tag = "ALERT" if resp.ok and resp.json().get("violation") else "ok"
                print(f"[{s['sensor_code']}] {decibel_value:5.1f} dB -> {resp.status_code} ({tag})")
            except requests.RequestException as exc:
                print(f"[{s['sensor_code']}] failed to reach server: {exc}")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate ESP8266 noise sensor nodes")
    parser.add_argument("--server", default="http://localhost:5000", help="Backend base URL")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between readings")
    args = parser.parse_args()

    try:
        run(args.server, args.interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


# ---------------------------------------------------------------------
# Real firmware (ESP8266, Arduino C++) would follow the same contract:
#
#   POST {SERVER_URL}/api/readings
#   Headers: X-Sensor-Key: <sensor's api_key>
#   Body: {"decibel_value": 62.4, "recorded_at": "2026-09-14T10:15:00"}
#
# with local flash-memory buffering and retransmission on reconnect, as
# described in Appendix B of the project write-up.
# ---------------------------------------------------------------------
