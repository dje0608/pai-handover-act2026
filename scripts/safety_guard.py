#!/usr/bin/env python3
"""安全ガード：AI の指令をロボットに届ける前に確認し、危ない指令を止める。
AI 側は infer_with_guard.py で起動し、指令を /ai/arm_cmd と /ai/gripper_cmd に出す。
使い方：python3 ~/safety_guard.py               （通常）
        python3 ~/safety_guard.py --j1-max 0.15  （ガードが働く様子の確認用）
"""
import argparse
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

ARM_TOPIC = '/crane_plus_arm_controller/joint_trajectory'
GRIPPER_TOPIC = '/crane_plus_gripper_controller/joint_trajectory'
HAND = 'crane_plus_joint_hand'

# 角度の範囲 [rad]（ロボットの限界ではなく、受け渡しの動きに余裕を持たせた範囲）
DEFAULT_LIMITS = {
    'crane_plus_joint1': (-1.0, 1.0),
    'crane_plus_joint2': (-1.0, 1.0),
    'crane_plus_joint3': (-1.5, 1.5),
    'crane_plus_joint4': (-1.5, 1.5),
    HAND: (-0.7, 0.3),
}
MAX_STEP = 0.3   # 1回の指令で許す、今の角度からの差 [rad]
TIMEOUT = 1.0    # この秒数 AI の指令が来なければ、その場で止める
SHORT = {'crane_plus_joint1': 'j1', 'crane_plus_joint2': 'j2',
         'crane_plus_joint3': 'j3', 'crane_plus_joint4': 'j4', HAND: 'hand'}


class SafetyGuard(Node):
    def __init__(self, limits):
        super().__init__('safety_guard')
        self.limits = limits
        self.arm_pub = self.create_publisher(JointTrajectory, ARM_TOPIC, 10)
        self.gripper_pub = self.create_publisher(JointTrajectory, GRIPPER_TOPIC, 10)
        self.create_subscription(JointTrajectory, '/ai/arm_cmd', self.on_arm, 10)
        self.create_subscription(JointTrajectory, '/ai/gripper_cmd', self.on_gripper, 10)
        self.create_subscription(JointState, '/joint_states', self.on_state, 10)
        self.current = {}
        self.last_cmd_time = None
        self.stopped_for_timeout = False
        self.status = '待機中'
        self.counts = {'制限': 0, '停止(急変)': 0, '停止(途絶)': 0}
        self.t0 = time.time()
        self.last_check = time.time()
        self.lags = 0
        self.create_timer(0.1, self.check_timeout)
        self.create_timer(0.5, self.show)

    def on_state(self, msg):
        self.current.update(zip(msg.name, msg.position))

    def send(self, pub, names, positions):
        jt = JointTrajectory()
        jt.joint_names = list(names)
        pt = JointTrajectoryPoint()
        pt.positions = [float(p) for p in positions]
        pt.time_from_start.nanosec = int(0.1 * 1e9)
        jt.points.append(pt)
        pub.publish(jt)

    def clamp(self, name, value):
        lo, hi = self.limits[name]
        return min(max(value, lo), hi)

    def on_arm(self, msg):
        self.last_cmd_time = time.time()
        self.stopped_for_timeout = False
        if not msg.points or not self.current:
            return
        names = msg.joint_names
        cmd = msg.points[0].positions
        # 確認1：急な指令（今の角度から MAX_STEP より大きく離れた指令）→ その場で止める
        for n, c in zip(names, cmd):
            if abs(c - self.current.get(n, c)) > MAX_STEP:
                self.send(self.arm_pub, names, [self.current.get(k, 0.0) for k in names])
                self.status = f'停止(急変) {SHORT.get(n, n)}'
                self.counts['停止(急変)'] += 1
                return
        # 確認2：角度の範囲 → 範囲の端までに抑えて送る
        safe = [self.clamp(n, c) for n, c in zip(names, cmd)]
        over = [SHORT.get(n, n) for n, c, s in zip(names, cmd, safe) if c != s]
        if over:
            self.status = '制限 ' + ','.join(over)
            self.counts['制限'] += 1
        else:
            self.status = '正常'
        self.send(self.arm_pub, names, safe)

    def on_gripper(self, msg):
        if not msg.points:
            return
        names = msg.joint_names
        safe = [self.clamp(n, c) for n, c in zip(names, msg.points[0].positions)]
        self.send(self.gripper_pub, names, safe)

    def check_timeout(self):
        # 確認3：AI の指令が途絶えたら、その場で止める（1回だけ送る）
        now = time.time()
        lag = now - self.last_check
        self.last_check = now
        if lag > 0.5:
            # ガード自身の処理が遅れた直後は、届いた指令がたまっている可能性があるので判定を1回見送る
            self.lags += 1
            return
        if self.last_cmd_time is None or self.stopped_for_timeout or not self.current:
            return
        if time.time() - self.last_cmd_time > TIMEOUT:
            names = [n for n in DEFAULT_LIMITS if n != HAND]
            self.send(self.arm_pub, names, [self.current.get(n, 0.0) for n in names])
            self.status = '停止(途絶)'
            self.counts['停止(途絶)'] += 1
            self.stopped_for_timeout = True

    def show(self):
        c = self.current
        print(f"{time.time() - self.t0:5.1f}s "
              f"j1={c.get('crane_plus_joint1', 0.0):+.3f} "
              f"j2={c.get('crane_plus_joint2', 0.0):+.3f} "
              f"hand={c.get(HAND, 0.0):+.3f} {self.status}", flush=True)


def main():
    parser = argparse.ArgumentParser(description='AI の指令を確認する安全ガード')
    parser.add_argument('--j1-max', type=float, help='joint1 の上限を変える（確認用）')
    args = parser.parse_args()
    limits = dict(DEFAULT_LIMITS)
    if args.j1_max is not None:
        limits['crane_plus_joint1'] = (limits['crane_plus_joint1'][0], args.j1_max)
    print('安全ガード起動', flush=True)
    print(f"j1の範囲={limits['crane_plus_joint1']} 急変={MAX_STEP}rad 途絶={TIMEOUT}秒", flush=True)
    rclpy.init()
    node = SafetyGuard(limits)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        print('介入の回数:', node.counts, ' ガード自身の遅れ:', node.lags, '回', flush=True)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
