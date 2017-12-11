#!/usr/bin/env python

"""Plot sensor data."""

import os
import sys
from time import gmtime, strftime
import json
import requests
import numpy as np
import cv2

PIN = 59
LOCAL_STORE = 'pin_data_' + str(PIN)
TIME_SCALE_FACTOR = 60 * 2
DATA_SCALE_FACTOR = 2
RECENT = {'time': None}

def api_url():
    major_version = int(os.getenv('FARMBOT_OS_VERSION', '0.0.0')[0])
    base_url = os.environ['FARMWARE_URL']
    return base_url + 'api/v1/' if major_version > 5 else base_url

def post(wrapped_data):
    """Send the Celery Script command."""
    headers = {
        'Authorization': 'bearer {}'.format(os.environ['FARMWARE_TOKEN']),
        'content-type': "application/json"}
    payload = json.dumps(wrapped_data)
    requests.post(api_url() + 'celery_script',
                  data=payload, headers=headers)

def no_data_error():
    """Send an error to the log if there's no data."""
    wrapped_message = {
        "kind": "send_message",
        "args": {
            "message_type": "error",
            "message": "[Plot sensor data] No data available."}}
    post(wrapped_message)

def get_pin_data():
    """Get existing historical pin data."""
    data = json.loads(os.getenv(LOCAL_STORE, '[]'))
    if len(data) < 1:
        no_data_error()
        sys.exit(0)
    else:
        return data

def reduce_data(data):
    """Reduce the loaded data for plotting."""
    times, values = [], []
    for record in data:
        times.append(round(float(record['time']) / TIME_SCALE_FACTOR))
        values.append(round(float(record['value']) / DATA_SCALE_FACTOR))
    RECENT['time'] = max(times) * TIME_SCALE_FACTOR
    times = abs(np.array(times) - max(times))
    all_data = np.column_stack((times, values))
    filtered_data = all_data[all_data[:, 0] < 720 ]
    return filtered_data

def plot(data):
    """Plot the reduced data."""
    # Create blank plot
    p = np.full([512, 24 * 60 / 2], 255, np.uint8)
    # Add shaded plot areas
    for i in range(512):
        if i < 100:  # N/A
            p[i, :] = 220
        elif i > 425:  # off
            p[i, :] = 220
        else:  # sensor range (gradient)
            p[i, :] = 255 - 175 * ((i - 100) / float(425 - 100))
    # Add horizontal gridlines
    for i in range(0, 512, 32):
        p[i, :] = 100
        if i == 384:
            p[i, :] = 125
    # Add minor vertical gridlines
    for i in range(0, 720, 30):
        p[:, i] = 100
    # Add major vertical gridlines
    for i in range(0, 720, 90):
        p[:, i - 1:i + 1] = 100
    # Add plot border
    cv2.rectangle(p, (0, 0), (719, 511), 50, 4)
    # Add data
    for record in data:
        time = int(record[0])
        value = int(record[1])
        cv2.circle(p, (time, value), 5, 0, 3)
    # Flip plot to display oldest to newest, low to high
    p = cv2.flip(p, -1)
    # Create plot border label area
    border = np.full([800, 600], 255, np.uint8)
    def _add_labels(image_area, labels):
        for label in labels:
            cv2.putText(image_area, label['text'].upper(),
                        label['position'], 0, 0.5, 0, 1)
    # Add sensor range text
    range_labels = [{'text': 'off', 'position': (500, 25)},
                    {'text': 'wet', 'position': (425, 25)},
                    {'text': 'dry', 'position': (160, 25)},
                    {'text': 'n/a', 'position': (75, 25)}]
    _add_labels(border, range_labels)
    # Flip labels to display vertically
    full = cv2.flip(cv2.transpose(border), 0)
    # Add sensor value labels
    value_labels = [{'text': '0', 'position': (760, 560)},
                    {'text': '512', 'position': (760, 305)},
                    {'text': '1023', 'position': (760, 50)}]
    _add_labels(full, value_labels)
    # Add most recent time
    time_string = strftime('%b %d %H:%M UTC', gmtime(RECENT['time']))
    _add_labels(full, [{'text': time_string, 'position': (650, 580)}])
    # Add time offset labels
    for i, column in enumerate(range(10, 600, 90)[::-1]):
        _add_labels(full, [{'text': '-{} hr'.format(6 + i * 3),
                            'position': (column, 580)}])
    # Add label area to plot area
    full[44:556, 40:760] = p
    # Add plot title
    cv2.putText(full, 'soil sensor'.upper(), (325, 25), 0, 0.75, 0, 2)
    return full

def save(image):
    """Save the plot image."""
    cv2.imwrite(os.environ['IMAGES_DIR'] + '/sensor_data_plot.png', image)

if __name__ == "__main__":
    save(plot(reduce_data(get_pin_data())))
