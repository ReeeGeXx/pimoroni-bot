import threading
import atexit
import RPi.GPIO as GPIO
from pimoroni_bot.robot import RobotController
from pimoroni_bot.video_stream import app

if __name__ == '__main__':
    # Start robot movement in a separate thread
    robot = RobotController()
    robot_thread = threading.Thread(target=robot.move_forward, kwargs={'speed': 0.5, 'duration': 5})
    robot_thread.start()
    print("Starting Flask server on http://0.0.0.0:5002 ...")
    app.run(host='0.0.0.0', port=5002)
    atexit.register(GPIO.cleanup)