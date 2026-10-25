#!/usr/bin/env python3
"""infer.py を書き換えずに、AI の指令の送り先を安全ガード用のトピックに付け替えて起動する。
使い方: cd ~/pai_training && pixi run python ~/infer_with_guard.py --model-path <モデルのフォルダ>
"""
import sys
import runpy
import rclpy

INFER = '/home/ubuntu/pai_training/scripts/infer.py'
REMAP = [
    '--ros-args',
    '-r', '/crane_plus_arm_controller/joint_trajectory:=/ai/arm_cmd',
    '-r', '/crane_plus_gripper_controller/joint_trajectory:=/ai/gripper_cmd',
]

_original_init = rclpy.init


def _init_with_remap(*args, **kwargs):
    # infer.py が rclpy.init() を呼んだときに、リマップの設定を渡す
    kwargs['args'] = ['infer.py'] + REMAP
    return _original_init(**kwargs)


rclpy.init = _init_with_remap
rclpy.shutdown = lambda *a, **k: rclpy.try_shutdown()  # Ctrl+C 時の二重終了エラーを防ぐ
sys.argv = [INFER] + sys.argv[1:]
runpy.run_path(INFER, run_name='__main__')
