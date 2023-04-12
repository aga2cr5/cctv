# CCTV

A simple webcam cctv for monitoring spaces. This application has a web interface to check on the video stream. In case movement is detected, the program saves the recording into a file.

To install this application run:

´´´ bash
pip3 install -r requirements.txt
´´´

You should also modify the code and change which VideoCapture device the program should use.

You should also preferrable create a new low priviledge user for the program to run on and add that user to the video group.

´´´ bash
sudo adduser cctv
sudo usermod -a -G video cctv
´´´

