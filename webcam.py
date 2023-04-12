#!/usr/bin/env python3

from flask import Flask, Response
import cv2
import time
import datetime

app = Flask(__name__)
cap = cv2.VideoCapture(4)

if not cap.isOpened():
    print("Cannot open camera")
    exit()
mog = cv2.createBackgroundSubtractorMOG2()

SECONDS_TO_RECORD_AFTER_DETECTION = 5

frame_size = (int(cap.get(3)), int(cap.get(4)))
fourcc = cv2.VideoWriter_fourcc(*"mp4v")


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

        if len(contours) > 0:
            if detection:
                timer_started = False
            else:
                detection = True
                current_time = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
                out = cv2.VideoWriter(f"{current_time}.mp4", fourcc, 20, frame_size)
                print("Started Recording!")
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
