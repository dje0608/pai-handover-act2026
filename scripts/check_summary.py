import glob, os, sys
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import JointState

folder = sys.argv[1] if len(sys.argv) > 1 else 'handover'
J = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint3', 'crane_plus_joint4']
for d in sorted(glob.glob(os.path.expanduser(f'~/dataset/rosbags/{folder}/ep*'))):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=d, storage_id='sqlite3'),
                rosbag2_py.ConverterOptions('cdr', 'cdr'))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/joint_states']))
    t0 = t1 = None
    first, last = {}, {}
    while reader.has_next():
        topic, data, t = reader.read_next()
        msg = deserialize_message(data, JointState)
        t0 = t if t0 is None else t0
        t1 = t
        for n, v in zip(msg.name, msg.position):
            first.setdefault(n, v)
            last[n] = v
    dur = (t1 - t0) / 1e9 if t0 else 0
    parts = [f"j{i+1} {last.get(j, 0):+.2f}" for i, j in enumerate(J)]
    h = 'crane_plus_joint_hand'
    hand = f"グリッパ {first.get(h, 0):+.2f}→{last.get(h, 0):+.2f}"
    print(f"{os.path.basename(d)}: 長さ {dur:5.1f}秒 | 終了角度 " + " ".join(parts) + f" | {hand}")
