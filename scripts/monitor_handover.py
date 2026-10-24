import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class Monitor(Node):
    def __init__(self):
        super().__init__('handover_monitor')
        self.last = 0.0
        self.start = time.time()
        self.create_subscription(JointState, '/joint_states', self.cb, 10)

    def cb(self, msg):
        now = time.time()
        if now - self.last < 0.5:
            return
        self.last = now
        p = dict(zip(msg.name, msg.position))
        j1 = p.get('crane_plus_joint1', 0.0)
        j2 = p.get('crane_plus_joint2', 0.0)
        h = p.get('crane_plus_joint_hand', 0.0)
        print(f"経過 {now - self.start:5.1f}秒  joint1 = {j1:+.3f}  joint2 = {j2:+.3f}  グリッパ = {h:+.3f}", flush=True)

rclpy.init()
rclpy.spin(Monitor())
