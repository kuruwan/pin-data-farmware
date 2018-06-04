#!/usr/bin/env python

"""Save sensor data."""

import os
import sys
import json
from time import time
import requests

FARMWARE_NAME = 'save_sensor_data'
HEADERS = {
    'Authorization': 'bearer {}'.format(os.environ['FARMWARE_TOKEN']),
    'content-type': 'application/json'}

def get_env(key, type_=int):
    """Return the value of the namespaced Farmware input variable."""
    return type_(os.getenv('{}_{}'.format(FARMWARE_NAME, key), 59))

def no_data_error():
    """Send an error to the log if there's no data."""
    message = '[Save sensor data] Pin {} value not available.'.format(PIN)
    wrapped_message = {
        'kind': 'send_message',
        'args': {
            'message_type': 'error',
            'message': message}}
    post(wrapped_message)

def get_pin_value(pin):
    """Get the value read by a Sequence `Read Pin` step or the Sensor widget."""
    response = requests.get(
        os.environ['FARMWARE_URL'] + 'api/v1/bot/state',
        headers=HEADERS)
    try:
        value = response.json()['pins'][str(pin)]['value']
    except KeyError:
        value = None
    if value is None:
        no_data_error()
        sys.exit(0)
    return value

def timestamp(value):
    """Add a timestamp to the pin value."""
    return {'time': time(), 'value': value}

def append(data):
    """Add new data to existing data."""
    try:
        existing_data = json.loads(os.environ[LOCAL_STORE])
    except KeyError:
        existing_data = []
    existing_data.append(data)
    return existing_data

def wrap(data):
    """Wrap the data in a `set_user_env` Celery Script command to save it."""
    return {
        'kind': 'set_user_env',
        'args': {},
        'body': [{
            'kind': 'pair',
            'args': {
                'label': LOCAL_STORE,
                'value': json.dumps(data)
            }}]}

def post(wrapped_data):
    """Send the Celery Script command."""
    payload = json.dumps(wrapped_data)
    requests.post(os.environ['FARMWARE_URL'] + 'api/v1/celery_script',
                  data=payload, headers=HEADERS)

if __name__ == '__main__':
    PIN = get_env('pin')
    LOCAL_STORE = 'pin_data_' + str(PIN)
    post(wrap(append(timestamp(get_pin_value(PIN)))))
