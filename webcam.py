#!/usr/bin/env python3

from dotenv import load_dotenv
from os import getenv
import cv2
import time
import datetime
import subprocess
import requests
import json

load_dotenv()

MATTERMOST_WEBHOOK = getenv("MATTERMOST_WEBHOOK")
SECONDS_TO_RECORD_AFTER_DETECTION = 10
TIME_TO_START_FILMING_AFTER_DOOR_OPENING = 1800


# The capture device needs to be changed according to the webcam used
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    exit()

mog = cv2.createBackgroundSubtractorMOG2()
frame_size = (int(cap.get(3)), int(cap.get(4)))
fourcc = cv2.VideoWriter_fourcc(*"mp4v")


def send_notification_to_mattermost(url, message):
    """Sends notifications to mattermost through a webhook"""
    default_headers = {"content-type": "application/json"}
    message = {"text": str(message)}
    try:
        response = requests.post(url, data=json.dumps(message), headers=default_headers)
        if response.status_code != 200:
            raise Exception(
                f"Http request to mattermost failed: {response.status_code}"
            )
    except Exception as err:
        print(f"Could not send message to mattermost because:\n{err}")


def get_door_log():
    """This ssh connection is using key based authentication. Returns time in unix time format"""
    try:
        response = subprocess.run(
            "ssh cctv@192.168.1.20 tail -n 1 /home/av/electric_door_log.txt",
            shell=True,
            capture_output=True,
        )
        time_in_unix = int(response.stdout.strip().split(b" ")[-1])
        return time_in_unix

    except Exception as err:
        message = err
        send_notification_to_mattermost(MATTERMOST_WEBHOOK, message)
    # if this fails then it says that the door has been opened like 30 mins before
    return time.time() - 1800


def process_image(frame):
    """Image processsing here"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    fgmask = mog.apply(gray)

    # Apply morphological operations to reduce noise and fill gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fgmask = cv2.erode(fgmask, kernel, iterations=1)
    fgmask = cv2.dilate(fgmask, kernel, iterations=1)

    return fgmask


def generate_frame(cap):
    """Generates a frame for the video stream"""
    detection = False
    detection_stopped_time = None
    timer_started = False
    last_login_checked_time = None

    while True:
        ret, frame = cap.read()
        fgmask = process_image(frame)

        contours, hierarchy = cv2.findContours(
            fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter moving targets to include only targets with area larger than 2000 pixels
        moving_targets = list(
            filter(lambda contour: cv2.contourArea(contour) > 2000, contours)
        )

        if len(moving_targets) > 0:
            time_now = time.time()
            # check last login time every 3 minutes to reduce unnecessary ssh connections
            if (
                last_login_checked_time == None
                or time_now - last_login_checked_time > 300
            ):
                last_login = get_door_log()

            if detection:
                timer_started = False

            elif time_now - last_login > TIME_TO_START_FILMING_AFTER_DOOR_OPENING:
                detection = True
                current_time = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
                out = cv2.VideoWriter(f"{current_time}.mp4", fourcc, 20, frame_size)
                message = "Started Recording!"
                send_notification_to_mattermost(MATTERMOST_WEBHOOK, message)

        elif detection:
            if timer_started:
                if (
                    time.time() - detection_stopped_time
                    >= SECONDS_TO_RECORD_AFTER_DETECTION
                ):
                    detection = False
                    timer_started = False
                    out.release()
                    message = "Stop Recording!"
                    send_notification_to_mattermost(MATTERMOST_WEBHOOK, message)
            else:
                timer_started = True
                detection_stopped_time = time.time()
        if detection:
            out.write(frame)


if __name__ == "__main__":
    try:
        send_notification_to_mattermost(MATTERMOST_WEBHOOK, "CCTV system started!")
        generate_frame(cap)
    except KeyboardInterrupt:
        send_notification_to_mattermost(MATTERMOST_WEBHOOK, "CCTV system stopped!")
        print("\nExiting the program\n")
        exit()
