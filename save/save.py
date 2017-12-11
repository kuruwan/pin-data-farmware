#!/usr/bin/env python

"""Save sensor data."""

import os
import sys
import json
from time import time
import requests
try:
  import redis
  legacy = True
except ImportError:
  legacy = False

headers = {
  'Authorization': 'bearer {}'.format(os.environ['FARMWARE_TOKEN']),
  'content-type': "application/json"}

PIN = 59
LOCAL_STORE = 'pin_data_' + str(PIN)

def no_data_error():
    """Send an error to the log if there's no data."""
    wrapped_message = {
        "kind": "send_message",
        "args": {
            "message_type": "error",
            "message": "[Save sensor data] Pin value not available."}}
    post(wrapped_message)

def get_pin_value(pin):
    """Get the value read by a Sequence `Read Pin` step."""
    if legacy:
        r = redis.Redis()
        value = r.get('BOT_STATUS.pins.{}.value'.format(pin))
    else:
        response = requests.get(
            os.environ['FARMWARE_URL'] + 'api/v1/bot/state',
            headers=headers)
        try:
            value = response.json()['pins'][str(PIN)]['value']
        except KeyError:
            value = None
    if value is None:
        no_data_error()
        sys.exit(0)
    return value

def timestamp(value):
    """Add a timestamp to the pin value."""
    return {"time": time(), "value": value}

def append(data):
    """Add new data to existing data."""
    try:
        existing_data = json.loads(os.environ[LOCAL_STORE])
    except KeyError:
        existing_data = []
    else:
        existing_data.append(data)
    return existing_data

def wrap(data):
    """Wrap the data in a `set_user_env` Celery Script command to save it."""
    return {
        "kind": "set_user_env",
        "args": {},
        "body": [{
            "kind": "pair",
            "args": {
                "label": LOCAL_STORE,
                "value": json.dumps(data)
            }}]}

def post(wrapped_data):
    """Send the Celery Script command."""
    payload = json.dumps(wrapped_data)
    api_path = '' if legacy else 'api/v1/'
    requests.post(os.environ['FARMWARE_URL'] + api_path + 'celery_script',
                  data=payload, headers=headers)

if __name__ == "__main__":
    post(wrap(append(timestamp(get_pin_value(PIN)))))
