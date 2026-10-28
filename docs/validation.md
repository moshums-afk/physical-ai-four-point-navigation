# 公開用パッケージの検証記録

確認日：2026-10-27。

追記：2026-10-28の本人によるGUI走行・録画・再生の確認、および起動・録画の修正は [handson_validation.md](handson_validation.md) に記録しています。以下は2026-10-27時点の記録です。

## 実施した確認

- `docker compose config --quiet` が成功。
- 指定した教材イメージから一時コンテナを作成し、既存コンテナの追加設定に依存せず実行。
- `tools/check_environment.py` で、Python 3.10.12、NumPy 1.24.4、ROS 2 Humble、Gazebo 6.16.0、ros_gz_bridgeと必要ファイルを確認。
- `tools/verify_evidence.py` で63ファイルの一致、保存モデル、元の3試行の到達順・距離・停止条件を確認。
- `test_waypoints.py` の7件が成功。順序を飛ばさないこと、最終停止、到達と停止の両方が必要なこと、古い通信で成功しないこと、旋回時の基準点などを確認。
- READMEの起動手順に結果名を付けた以下のコマンドで、GUIなしの4点走行を通し実行。

```bash
docker compose run --rm --no-deps --entrypoint bash ros /workspace/tools/run_headless.sh package_validation_20261027
```

起動・接続確認・4点走行・停止・起動したGazeboとbridgeの終了まで完了し、コマンドは終了コード0を返しました。一時コンテナは `--rm` で終了時に削除されました。

## 今回の再現結果

元の録画（2026-10-26）の結果と混同しないよう、公開用パッケージの確認試行として別に保存しています。

| 項目 | 値 |
|---|---|
| 成功判定 | true |
| 通過順 | 1 → 2 → 3 → 4 |
| 各点の採点距離 | 0.182、0.189、0.190、0.199 m |
| 最終停止後の距離 | 0.166511 m |
| 最終odometry速度 | 0 m/s、0 rad/s |
| 停止保持 | 完了 |
| シミュレーション時間 | 24.706秒 |
| 実時間 | 48.298秒 |

[条件](validation_run/protocol.json)、[最終結果](validation_run/summary.json)、[各点の到達](validation_run/visits.json)、[軌跡CSV](validation_run/trajectory.csv) を同梱しました。READMEの主要結果0.172 mは元の録画試行の値であり、今回の0.166511 mへ置き換えていません。

## 検証していないこと

このPCで既に取得済みのイメージを使いました。リモートからのイメージ新規取得、別PCへの初回導入、異なるCPUアーキテクチャ、GUI録画・動画合成、再学習の通し実行は今回の検証に含みません。再現確認1回を多数回の信頼性評価とは扱いません。

2026-10-27の初版PDFは、その作成時点では手順の通し確認が未実施でした。その後の本人操作による検証を経て、2026-10-29の同梱PDFは公開用Composeの手順と再現結果を反映した6ページ版へ更新しています。初回パッケージ確認は本ファイル、本人の確認結果は `handson_validation.md` に分けて記録しています。
