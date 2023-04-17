# CCTV

A simple webcam cctv for monitoring spaces. This application has a web interface to check on the video stream. In case movement is detected, the program saves the recording into a file.

To install this application run:

``` bash
pip3 install -r requirements.txt
```

You should also modify the code and change which VideoCapture device the program should use.

Create a .env file and with the following content. Remember to replace "your_webhook_here" with your webhook:

``` bash
MATTERMOST_WEBHOOK="your_webhook_here"
```

You should also preferrable create a new low priviledge user for the program to run on and add that user to the video group.

``` bash
sudo adduser cctv
sudo usermod -a -G video cctv
```
