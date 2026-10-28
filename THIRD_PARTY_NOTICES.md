# 出典、ライセンス、変更点

## Gazebo / gz-sim

Gazeboプロジェクトの `gz-sim`（`ign-gazebo6` 系列）を参照し、インストール済みGazebo Fortress 6.16.0のサンプルからシーンとGUI設定を生成しました。

| 同梱ファイル | 元のファイル・使用範囲 |
|---|---|
| `final_project/diff_drive_smoke/world.sdf` | 差動二輪サンプルの車体、車輪、キャスター、駆動プラグイン等を変更 |
| `final_project/diff_drive_smoke/world_waypoints.sdf` | 上記のシーンに4地点・番号・白い基準点を追加 |
| `final_project/diff_drive_smoke/gui.config` | GazeboのGUI設定を変更 |
| `final_project/diff_drive_smoke/gui_waypoints.config` | 上記から4点走行向けの画角・サイズ・表示項目へ変更 |

参照先：

- [差動二輪サンプル](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/examples/worlds/diff_drive.sdf)
- [GUI設定](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/gui/gui.config)
- [上流ライセンス](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/LICENSE)
- [PosePublisher実装](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/systems/pose_publisher/PosePublisher.cc)
- [ROS 2との連携](https://gazebosim.org/docs/fortress/ros2_integration/)

上流のApache License 2.0原文を [LICENSES/gazebo-Apache-2.0.txt](LICENSES/gazebo-Apache-2.0.txt) に同梱しました。2026-10-27に公式リポジトリのLICENSEから取得したものです。リンク先のブランチ内容は更新される可能性があり、実験時のファイルとの完全一致を意味しません。

変更は、車体を2台から1台へ減らすこと、影の無効化、床の寸法、ROS用トピック、モデル位置配信、目標マーカー、4点の番号、白い車輪軸中央マーカー、GUIの画角・サイズ・表示プラグイン等です。該当する同梱ファイルに変更・出典のコメントを付けました。コメント追加前後のハッシュは [docs/source_manifest.json](docs/source_manifest.json) で対応付けています。

`prepare_scene.py` と `prepare_waypoint_scene.py` は、インストール済みサンプルを加工するために本作品で追加したスクリプトです。公開用の再生成には `tools/prepare_scenes.py` を使い、生成ファイルにも出典コメントを残します。

## 本作品で追加した内容

教師データ生成、学習・NumPy推論、4点の順序管理、座標変換、評価・記録、録画補助、説明文・図、および公開用の起動・検証補助は、本作品のために追加したものです。この準備段階では、それら独自部分への追加の再利用ライセンスを設定していません。第三者由来部分に適用されるライセンスを変更するものではありません。

保存教師データはコード内のルールから生成した状態・速度の組です。講義PDF、講義の実習データセット、環境の復旧記録、デスクトップ録画は、このリポジトリには同梱していません。

## 実行時の依存関係

ROS 2、Gazebo、NumPy、PyTorch、Pillow、matplotlib、ffmpeg等はそれぞれのプロジェクトのライセンスに従います。このリポジトリはそれらのプログラム本体やDockerイメージを再配布せず、使用イメージ・必要環境を指定します。
