import glob, os
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import JointState

KEYS = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint_hand']
TH = 0.005
STILL = 0.0005

for d in sorted(glob.glob(os.path.expanduser('~/dataset/rosbags/handover/ep*'))):
    r = rosbag2_py.SequentialReader()
    r.open(rosbag2_py.StorageOptions(uri=d, storage_id='sqlite3'),
           rosbag2_py.ConverterOptions('cdr', 'cdr'))
    r.set_filter(rosbag2_py.StorageFilter(topics=['/joint_states']))
    s = []
    while r.has_next():
        topic, data, t = r.read_next()
        m = deserialize_message(data, JointState)
        p = dict(zip(m.name, m.position))
        if all(k in p for k in KEYS):
            s.append((t, [p[k] for k in KEYS]))
    first, last = s[0][1], s[-1][1]
    i0 = next(i for i, (t, v) in enumerate(s) if any(abs(a - b) > TH for a, b in zip(v, first)))
    i1 = max(i for i, (t, v) in enumerate(s) if any(abs(a - b) > TH for a, b in zip(v, last)))
    longest, run_start, where = 0.0, None, None
    for i in range(i0 + 1, i1 + 1):
        still = all(abs(a - b) < STILL for a, b in zip(s[i][1], s[i - 1][1]))
        if still:
            if run_start is None:
                run_start = s[i - 1][0]
            dur = (s[i][0] - run_start) / 1e9
            if dur > longest:
                longest, where = dur, s[i][1]
        else:
            run_start = None
    if where:
        print(f"{os.path.basename(d)}: 動作中の最長の停止 {longest:.2f}秒 "
              f"（そのときの姿勢 joint1 {where[0]:+.2f} / joint2 {where[1]:+.2f} / グリッパ {where[2]:+.2f}）")
    else:
        print(f"{os.path.basename(d)}: 動作中の停止なし")
