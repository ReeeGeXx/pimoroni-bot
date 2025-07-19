import atexit
import RPi.GPIO as GPIO
from pimoroni_bot.video_stream import app

atexit.register(GPIO.cleanup)

if __name__ == '__main__':
    print("Starting Flask server on http://0.0.0.0:5002 ...")
    app.run(host='0.0.0.0', port=5002)