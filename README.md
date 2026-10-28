# 軽量な模倣学習による3D移動ロボットの4点通過

ROS 2とGazeboで、差動二輪ロボットを **P1 → P2 → P3 → P4** の順に走らせ、最後に停止させる作品です。学習済みニューラルネットワークが目標までの距離と方向のずれから、前進速度・旋回速度を決めます。

- [説明レポート（PDF・ID88589）](docs/report.pdf) / [編集用Markdown](docs/report.md)
- [コードの公開先（GitHub）](https://github.com/moshums-afk/physical-ai-four-point-navigation)
- [再現手順](docs/reproduction.md) / [環境と検証範囲](docs/environment.md)
- [2026-10-28〜29の本人操作による再現確認](docs/handson_validation.md)：GUI表示、4点走行、録画保存・再生、CPU再学習を確認。再学習した重みは元モデルと一致。起動と録画で見つかった問題と修正も記録。
- [動作動画（YouTube）](https://youtu.be/YEbQuHdJQwY)

![録画試行の実測軌跡](docs/assets/four_points_trajectory.png)

## 何を確認したか

2026-10-26の録画試行では、全4点に指定順で到達し、停止後の最終距離は **0.172 m**、最終odometry速度は **0 m/s・0 rad/s** でした。シミュレーション時間24.607秒に対して実時間は81.657秒です。数値は [元ログ](evidence/four_points_recorded_20261026_v2/summary.json) に対応します。

| 条件 | 定義 |
|---|---|
| 目標 (m) | P1 (1.5, 0.0)、P2 (1.5, 1.5)、P3 (0.0, 1.5)、P4 (0.0, 3.0) |
| 位置基準 | 左右の駆動輪を結ぶ車輪軸の中央 |
| 開始姿勢 | モデル原点 (0, 0, yaw=0)。車輪軸中央は約 (0.554, 0) m |
| 目標切り替え | odometry推定で現在の目標から0.20 m以内 |
| 通過の採点 | 切り替え時のGazebo位置を車輪軸中央へ換算し、各目標から0.25 m以内 |
| 最終停止 | P4到達後にゼロ速度を1シミュレーション秒以上指令。最終距離0.25 m以内、直進・旋回の最終速度絶対値は各0.03以下（m/s・rad/s） |
| 時間上限 | 120シミュレーション秒、360実秒 |

「通過」は中心座標への完全一致ではなく、指定順に許容範囲へ入ることです。開始時に1回だけ位置と座標を合わせ、途中の地点ではリセットしません。P1〜P3には停止保持を設けません。

## AIと通常のプログラムの分担

**AI** は距離と角度差から速度を出力します。モデルは2 → 32 → 32 → 2の全結合ネットワークで、1,218パラメータ。ルール教師から24,000組のデータを作り、CPUで学習しました。人の実演データではありません。別seedの検証データは6,000組です。

**通常のプログラム** は目標の順序、切り替え、最終停止、速度上限、通信監視を担当します。初期合わせ後の制御には車輪odometryを使い、Gazebo位置は通過の採点に使います。走行中も評価用位置の通信を監視しています。

モデルの再学習や経路探索で4点を覚えさせた構成ではなく、同じ保存重みを各目標に繰り返し使います。

## 最短で実行する

Docker EngineまたはDocker Desktop（Linuxコンテナ）、Docker Compose v2が必要です。WindowsではWSL 2を有効にしてください。以下は、リポジトリのルートで実行します。初回は教材イメージの取得に時間がかかります。

```bash
docker compose run --rm --no-deps --entrypoint bash ros /workspace/tools/run_headless.sh
```

環境確認 → 保存物の整合性検証 → 7件のロジックテスト → 4点走行の順に進みます。GUIは起動しません。終了時に、この起動処理が作ったシミュレータと通信処理を終了します。新しい結果は `final_project/diff_drive_smoke/results/four_points_日時/summary.json` に保存されます。

保存結果の確認とロジックテストだけなら、DockerやROSを使わずPython 3.10以降でも実行できます。

```bash
python tools/verify_evidence.py
python -m unittest discover -s final_project/diff_drive_smoke -p test_waypoints.py -v
```

GUIでの表示、録画、再学習、失敗時の確認方法は [再現手順](docs/reproduction.md) に記載しています。

## 失敗と修正、検証の範囲

| 試行 | 結果 |
|---|---|
| [初期版・GUIなし](evidence/four_points_headless_20261026_v1/summary.json) | P1のみ到達。120.024シミュレーション秒で時間切れ |
| [修正版・GUIなし](evidence/four_points_headless_20261026_v2/summary.json) | 4点到達・停止成功。最終距離0.168 m |
| [修正版・録画あり](evidence/four_points_recorded_20261026_v2/summary.json) | 4点到達・停止成功。最終距離0.172 m |

車輪軸中央とモデル原点は前後に0.5542825 m離れています。初期版の失敗を受け、制御・通過判定・表示の基準を車輪軸中央に統一しました。前後で位置基準とシーンが変わるため、完全に同一条件での精度比較とは扱いません。

元の結果は障害物のない1コース・同じ開始姿勢に限ります。単一目標の5条件・追加3条件のログは [別フォルダ](evidence/single_goal/) にあり、4点タスクの成功回数へ合算しません。実機、障害物回避、SLAM、広範囲の汎化、教師ルールに対する優位性は未検証です。

## フォルダ構成

```text
compose.yaml                       固定した教材イメージと共有フォルダ
final_project/diff_drive_smoke/     使用コード、シーン、GUI設定
  learned/                         保存重み、教師データ、学習記録
  results/                         新しい実行結果（Gitの対象外）
evidence/                          提出説明の根拠となる保存ログ
docs/                              説明資料、再現手順、環境、出典記録
tools/                             公開用の確認・起動補助
LICENSES/                          同梱した第三者ライセンス
THIRD_PARTY_NOTICES.md              出典と変更点
```

`evidence/` の元ログは変更せず保存しています。公開用のSDF・GUIには出典コメントを追加したため、ファイルのハッシュは録画時と異なります。幾何形状や制御設定は変更していません。対応は [source_manifest.json](docs/source_manifest.json)、検証結果は [validation.md](docs/validation.md) を参照してください。

Gazebo公式の車体・駆動サンプルを土台にしています。今回追加したのは教師データ生成、学習・推論、4点の順序管理、基準点の統一、評価・記録などです。第三者由来部分の出典とライセンスは [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) にまとめています。
