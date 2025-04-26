from flask import Flask, jsonify
import os, datetime, pytz, json, openai
from garminconnect import Garmin, GarminConnectAuthenticationError

TZ = pytz.timezone("Europe/Copenhagen")

app = Flask(__name__)

def get_garmin_client():
    try:
        return Garmin(
            email=os.getenv("GC_USER"),
            password=os.getenv("GC_PASS"),
            mfa=os.getenv("GC_TOTP") or None
        )
    except GarminConnectAuthenticationError as e:
        return None

def nightly_pull():
    g = get_garmin_client()
    if g is None:
        return {"error": "Garmin login failed"}

    today = datetime.datetime.now(TZ).date()
    start = today - datetime.timedelta(days=1)
    hrv = g.get_hrv_data(start.isoformat(), start.isoformat())  # yesterday
    body = g.get_body_battery(start.isoformat(), start.isoformat())

    payload = {
        "kind": "hrv",
        "date": str(start),
        "rmssd": hrv.get("rmssd"),
        "body_battery": body.get("bodyBattery", {}).get("dailyAverage")
    }

    openai.api_key = os.getenv("OPENAI_KEY")
    openai.beta.threads.messages.create(
        thread_id=os.getenv("THREAD_ID"),
        role="user",
        content=json.dumps(payload),
        assistant_id=os.getenv("ASSISTANT_ID")
    )
    return payload

@app.get("/garmin/pull")
def garmin_pull():
    data = nightly_pull()
    return jsonify(data)

@app.get("/")
def root():
    return "HealthGuide webhook is running"

if __name__ == "__main__":
    app.run()
