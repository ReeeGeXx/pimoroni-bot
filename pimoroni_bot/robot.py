try:
    from trilobot import Trilobot
except ImportError:
    Trilobot = None

class RobotController:
    def __init__(self):
        self.tbot = Trilobot() if Trilobot else None

    def move_forward(self, speed=0.5, duration=5):
        if self.tbot:
            self.tbot.forward(speed)
            import time
            time.sleep(duration)
            self.tbot.stop()
        else:
            print("Trilobot not available (simulated mode)") 