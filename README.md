# pai-handover-act

Physical AI 応用編1 最終課題：CRANE+ V2 による部品の受け渡し（Gazebo、ACT による模倣学習）

## 概要

ロボットアームが横を向き、腕を前に出し、グリッパを開いて部品を渡す動きを、人のキーボード操作の手本10回から ACT で学習させました。
手本の途中の「止まり」が AI の停止の原因になることを実験で見つけ、止まらない手本に録り直して、最後まで受け渡しを成功させました。

## ファイル構成

| パス | 内容 |
| --- | --- |
| scripts/check_summary.py | 記録した各回の長さ・最後の関節角度・グリッパの値を一覧表示 |
| scripts/check_pause.py | 動作中の最長の停止と、そのときの姿勢を表示 |
| scripts/trim_bags.py | 動き始めの0.5秒前から動き終わりの1秒後までを残し、前後の止まりを削除 |
| scripts/monitor_handover.py | AI が動かしている間の関節角度を表示 |
| scripts/monitor_video.py | 動画撮影用に、角度を短い形式で表示 |
| configs/conversion_config.yaml | 変換の設定（講義の pai_training の設定ファイルに、本課題の値を記入） |
| configs/train_config.yaml | 学習の設定（同上。学習2000回、CPU） |
| docker/run_pai_container.sh | コンテナの作成（ポートを 127.0.0.1 に限定し、自分の PC からだけ接続できるようにした） |

## 実行環境

- 講義で配布された Docker イメージ（ROS 2 Humble、Gazebo、crane_plus_gazebo）
- 講義で配布された pai_training（このリポジトリには含めていません）

## 作業の流れ

1. Gazebo を起動し、キーボード操作（physicalai_teleop）で手本を rosbag に記録（10回）
2. `check_summary.py` と `check_pause.py` で、各回の長さ・角度・止まりを確認
3. `trim_bags.py --write` で前後の止まりを削除
4. `configs/` の設定を pai_training に置き、`pixi run convert` で LeRobot 形式に変換
5. `pixi run train` で ACT を学習
6. `pixi run infer` で AI に動かし、`monitor_handover.py` で角度を確認

## 含めていないもの

- pai_training 本体（ライセンスの記載がないため）
- 記録データ・学習済みモデル（容量が大きいため）
