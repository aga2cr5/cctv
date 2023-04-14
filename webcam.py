#!/usr/bin/env python3

from flask import Flask, Response
import cv2
import time
import datetime
import subprocess
import requests
import json


SECONDS_TO_RECORD_AFTER_DETECTION = 10
TIME_TO_START_FILMING_AFTER_DOOR_OPENING = 1800
MATTERMOST_WEBHOOK = "https://chat.entropy.fi/hooks/ifqmnphi13rtpqdi65fe9jjw8h"


app = Flask(__name__)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    exit()
mog = cv2.createBackgroundSubtractorMOG2()


frame_size = (int(cap.get(3)), int(cap.get(4)))
fourcc = cv2.VideoWriter_fourcc(*"mp4v")


def send_notification_to_mattermost(url, message):
    default_headers = {"content-type": "application/json"}
    requests.post(url, data=json.dumps(message), headers=default_headers)


def get_door_log():
    try:
        response = subprocess.run(
            "ssh cctv@192.168.1.20 tail -n 1 /home/av/electric_door_log.txt",
            shell=True,
            capture_output=True,
        )
        time_in_unix = int(response.stdout.strip().split(b" ")[-1])
        return time_in_unix

    except Exception as err:
        message = err.message
        send_notification_to_mattermost(MATTERMOST_WEBHOOK, message)
    # if this fails then it says that the door has been opened like 30 mins before
    return time.time() - 1800


def process_image(frame):
    """Move the image processing stuff here from the gen method"""
    pass


def gen(cap):
    detection = False
    detection_stopped_time = None
    timer_started = False

    while True:
        ret, frame = cap.read()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fgmask = mog.apply(gray)

        # Apply morphological operations to reduce noise and fill gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fgmask = cv2.erode(fgmask, kernel, iterations=1)
        fgmask = cv2.dilate(fgmask, kernel, iterations=1)

        contours, hierarchy = cv2.findContours(
            fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # tässä voisi vielä miettiä haluaako jotenkin filtteröidä noita liikehavaintoja
        # if cv2.contourArea(contour) < 2000:
        moving_targets = list(
            filter(lambda contour: cv2.contourArea(contour) > 2000, contours)
        )
        # aikaisemmin tässä oli vain contours moving_targets sijasta
        if len(moving_targets) > 0:
            time_now = time.time()
            last_login = get_door_log()

            if detection:
                timer_started = False
            elif time_now - last_login > TIME_TO_START_FILMING_AFTER_DOOR_OPENING:
                detection = True
                current_time = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
                out = cv2.VideoWriter(f"{current_time}.mp4", fourcc, 20, frame_size)
                message = "Started Recording!"
                send_notification_to_mattermost(MATTERMOST_WEBHOOK, message)
                print(message)
        elif detection:
            if timer_started:
                if (
                    time.time() - detection_stopped_time
                    >= SECONDS_TO_RECORD_AFTER_DETECTION
                ):
                    detection = False
                    timer_started = False
                    out.release()
                    print("Stop Recording!")
            else:
                timer_started = True
                detection_stopped_time = time.time()

        if detection:
            out.write(frame)
        """
            # näkyykö kuvassa liikettä?
            # onko ovi avattu sähkölukolla?
            # kuinka kauan oven avaamisesta sähkölukolla on aikaa?
            # lähetetäänkö ilmoitus esim. telegramiin tai sähköpostiin?
            # laitetaanko esim. 10 sec välein kuvia telegramiin?
            # aloitetaanko tallennus?
            # mitä jos kameraan kajotaan? minne tallennetaan?
            # kuka pääsee näkemään tallenteen?

            # Draw bounding box around contour
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        """

        ret, jpeg = cv2.imencode(".jpg", frame)
        frame = jpeg.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n")


@app.route("/video_feed")
def video_feed():
    global cap
    return Response(gen(cap), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2204, threaded=True)
