import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class Monitor(Node):
    def __init__(self):
        super().__init__('video_monitor')
        self.last = 0.0
        self.start = time.time()
        self.create_subscription(JointState, '/joint_states', self.cb, 10)

    def cb(self, msg):
        now = time.time()
        if now - self.last < 0.5:
            return
        self.last = now
        p = dict(zip(msg.name, msg.position))
        print(f"{now - self.start:5.1f}s  j1={p.get('crane_plus_joint1', 0):+.3f}  "
              f"j2={p.get('crane_plus_joint2', 0):+.3f}  hand={p.get('crane_plus_joint_hand', 0):+.3f}", flush=True)

rclpy.init()
rclpy.spin(Monitor())
