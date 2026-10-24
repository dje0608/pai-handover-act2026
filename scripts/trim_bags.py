import glob, os, sys
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import JointState

SRC = os.path.expanduser('~/dataset/rosbags/handover')
DST = os.path.expanduser('~/dataset/rosbags/handover_trim')
WRITE = '--write' in sys.argv
KEYS = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint_hand']
TH = 0.005   # これ以上変化したら「動いた」とみなす
PRE = 0.5    # 動き始めの前に残す秒数
POST = 1.0   # 動き終わりの後に残す秒数

def open_reader(uri):
    r = rosbag2_py.SequentialReader()
    r.open(rosbag2_py.StorageOptions(uri=uri, storage_id='sqlite3'),
           rosbag2_py.ConverterOptions('cdr', 'cdr'))
    return r

for d in sorted(glob.glob(os.path.join(SRC, 'ep*'))):
    name = os.path.basename(d)
    r = open_reader(d)
    r.set_filter(rosbag2_py.StorageFilter(topics=['/joint_states']))
    series = []
    while r.has_next():
        topic, data, t = r.read_next()
        m = deserialize_message(data, JointState)
        p = dict(zip(m.name, m.position))
        if all(k in p for k in KEYS):
            series.append((t, [p[k] for k in KEYS]))
    t0, first = series[0]
    t_end, last = series[-1]
    move_start = next(t for t, v in series if any(abs(a - b) > TH for a, b in zip(v, first)))
    move_end = next(t for t, v in reversed(series) if any(abs(a - b) > TH for a, b in zip(v, last)))
    keep_from = max(t0, move_start - int(PRE * 1e9))
    keep_to = min(t_end, move_end + int(POST * 1e9))
    print(f"{name}: 全体 {(t_end - t0) / 1e9:5.1f}秒 | 開始前の静止 {(move_start - t0) / 1e9:4.1f}秒 | "
          f"動作 {(move_end - move_start) / 1e9:4.1f}秒 | 終了後の静止 {(t_end - move_end) / 1e9:4.1f}秒 | "
          f"切り出し後 {(keep_to - keep_from) / 1e9:4.1f}秒")
    if WRITE:
        out = os.path.join(DST, name)
        if os.path.exists(out):
            print(f"  {name}: 切り出し先がすでにあるため、スキップしました")
            continue
        w = rosbag2_py.SequentialWriter()
        w.open(rosbag2_py.StorageOptions(uri=out, storage_id='sqlite3'),
               rosbag2_py.ConverterOptions('cdr', 'cdr'))
        r2 = open_reader(d)
        for meta in r2.get_all_topics_and_types():
            w.create_topic(meta)
        while r2.has_next():
            topic, data, t = r2.read_next()
            if keep_from <= t <= keep_to:
                w.write(topic, data, t)
        del w
        print(f"  {name}: 切り出した記録を保存しました")
