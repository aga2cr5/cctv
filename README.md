# CCTV

A simple webcam cctv for monitoring spaces. In case movement is detected, the program saves the recording into a file.

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

To start the program you should just run it behind a screen or tmux. More sophisticated solution would be to run it as a service. Instructions on how to set this up will be added later on.
