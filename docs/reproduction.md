# 再現手順

このリポジトリを展開したフォルダを「リポジトリのルート」と呼びます。フォルダ名を変えても、ルートの `compose.yaml` と `final_project/` の位置関係を保てば利用できます。

## 1. 必要な環境

- Docker EngineまたはDocker DesktopのLinuxコンテナとCompose v2。
- Windowsの場合はWSL 2。Linux用プログラムはDocker内で実行します。
- 初回の教材イメージ取得にはインターネット接続が必要です。イメージは大きいため、ダウンロード時間と空き容量を確保してください。
- 使用イメージ、Python、NumPy等の版と検証範囲は [environment.md](environment.md) を参照。

以下は、ホストのPowerShellまたはWSL/Linux端末から、リポジトリのルートで実行します。

```bash
docker compose config --quiet
docker compose run --rm --no-deps --entrypoint bash ros /workspace/tools/run_headless.sh
```

このコマンドは同梱のシーンとモデルを使います。学習やシーン再生成は不要です。結果はホスト側にも残り、コンテナは終了後に削除されます。`results/` は実行時に作られます。

任意の結果名を付ける場合は末尾へ追加します。既存名は再利用しないでください。

```bash
docker compose run --rm --no-deps --entrypoint bash ros /workspace/tools/run_headless.sh replay_01
```

## 2. 結果の読み方

`final_project/diff_drive_smoke/results/replay_01/` に以下を保存します。

| ファイル | 内容 |
|---|---|
| `protocol.json` | 走行前に保存したコース、閾値、モデル・シーンのハッシュ |
| `visits.json` | 各点への到達順序、推定距離、Gazebo距離、時刻 |
| `trajectory.csv` | 各制御時刻の観測、速度指令、実位置、停止状態 |
| `summary.json` | 成否、最終距離・速度、時間、推論回数 |
| `timing.json` | 制御開始の時刻。録画との対応用 |

`summary.json` の `result.success` が `true`、`error` が `null`、`visits` の `point` が1・2・3・4、`hold_complete` が `true` になっているか確認します。元の録画結果は最終距離約0.172 mですが、実行時の負荷等により時間や距離は完全一致しません。

途中で失敗しても、保存されたログを残してください。新しい実験と2026-10-26の元ログを混ぜないため、元ログは `evidence/` に分けています。

## 3. 手順を1つずつ実行する

ホストからコンテナのシェルを開きます。

```bash
docker compose run --rm --no-deps --entrypoint bash ros
```

以降はコンテナ内です。

```bash
source /opt/ros/humble/setup.bash
export IGN_PARTITION=pai_delivery_smoke
cd /workspace
python3 tools/check_environment.py
python3 tools/verify_evidence.py
cd final_project/diff_drive_smoke
sha256sum learned/policy.npz
python3 start_demo.py --headless --waypoints
python3 evaluate_policy.py --probe
python3 run_waypoints.py --name replay_manual_01
python3 start_demo.py --stop
exit
```

起動直後に `--probe` が失敗した場合は少し待って再試行し、`truth`・`odom`・`sim` が取得できてから走行へ進みます。通常は1節の起動補助が接続確認と終了処理を行います。

保存モデルのSHA256：

```text
fa0ba22da8d10f839862cd06157fed283af6209e72b5f6b9bb2e7b2b2887a6b4
```

## 4. GUIで表示する

GUIなしの試走が終わってから、ホストのルートで起動します。

```bash
docker compose up -d
docker compose exec ros bash
```

`docker compose exec ros bash` で表示が `root@...` に変わったら、コンテナ内で実行します。

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=52 ROS_LOCALHOST_ONLY=1
cd /workspace/final_project/diff_drive_smoke
python3 start_demo.py --waypoints
```

ブラウザで [教材デスクトップ](http://localhost:6082/) を開きます。ロック解除等は教材イメージの案内に従い、車体・4つの番号・白い位置基準マーカーが見えることを確認します。録画中はこのデスクトップ全体が撮影されます。

起動補助はサーバーを `-s` で先に起動し、bridgeと `-g` のGUIを別プロセスで起動します。表示ありの場合は `gazebo`・`bridge`・`gui` の3つを記録し、`--stop` でまとめて終了します。サーバーとGUIの接続先は補助内で同じ `IGN_PARTITION` に設定します。

ブラウザ内のTerminatorを使う場合、最初は `ubuntu@...` の端末です。この教材環境ではrootが作成したログ・結果フォルダがあるため、まず `sudo -E bash` で `root@...` に切り替え、その後に上のsource・export・移動を行ってください。PowerShell、WSLのホスト端末、コンテナ内の端末は別の実行場所です。

同じコンテナ内で、表示確認後に実行します。

```bash
python3 /workspace/tools/check_environment.py --recording
python3 evaluate_policy.py --probe
python3 record_benchmark.py visible_01 --waypoints
python3 start_demo.py --stop
exit
```

ホストで終了します。

```bash
docker compose stop
```

`results/visible_01.mp4`、`visible_01_recording.json`、`visible_01/` が出力されます。車体が描画されない場合は [environment.md](environment.md) のOGRE2・表示確認を参照してください。

録画時はデスクトップの実寸を取得し、幅や高さが奇数なら右端・下端へ最大1ピクセルの余白を加えます。H.264/YUV420Pの出力サイズを偶数にし、画面全体を保持します。完了後はffmpegの終了状態とffprobeで動画の形式・サイズ・正の長さを確認してから `Saved` を表示します。`_recording.json` の `recording_success` と `video_validation` も確認できます。

## 5. 動画へ説明を付ける補助コード

`build_waypoint_video.py` は、録画ファイルと同じ名前の走行ログから説明カード・計測値を合成する補助です。元動画と同じ試行のログを使ってください。既存の提出動画を必ずこのコードで作成したという意味ではありません。

以下はコンテナ内で、`visible_01` の撮影が成功した後の例です。

```bash
cd /workspace/final_project/diff_drive_smoke
python3 build_waypoint_video.py visible_01 --speed 1 --output-name visible_01_edit
```

出力は `results/visible_01_edit/submission.mp4`。元の1920×1080のデスクトップとウィンドウ配置を前提に、動画領域を `(x=250, y=300, width=800, height=530)` で切り出します。配置が違う録画には、切り出し設定を調整してください。

時計の差だけから算出した開始位置は、録画処理の遅延を含む場合があります。実際の動画で動き始める位置を確認し、必要なら `--trim-start 秒数` で指定します。合成後は全編、計測値の同期、停止場面、1〜3分の尺を確認します。2倍速の場合は `--speed 2` で倍速表記が付きます。

## 6. 学習からやり直す

保存済みモデルを動かすだけならPyTorchは不要です。学習にはPyTorchが必要です。元の重みを残すため、別フォルダで行います。以下はコンテナ内のコマンドです。

```bash
source /opt/ros/humble/setup.bash
cd /workspace
python3 tools/check_environment.py --training
training_dir="/workspace/retrained/run_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$training_dir"
cp final_project/diff_drive_smoke/train_policy.py "$training_dir/"
cp final_project/diff_drive_smoke/policy.py "$training_dir/"
cd "$training_dir"
python3 train_policy.py
```

新しい `learned/` に重み、教師データ、学習曲線、設定・検証値が作られます。学習は24,000状態、別seedの検証6,000状態、CPU 1スレッド、Adam、学習率0.002、バッチ512、1,800更新です。データはルール教師から生成します。

新しいモデルで走らせる場合は、プログラム一式も別の実験コピーへ置き、そのコピーの `learned/policy.npz` を置き換えて評価します。付属ログは元の保存モデルの結果であり、再学習モデルの結果として流用しません。

## 7. シーンを再生成する場合

通常は同梱のシーンをそのまま使ってください。別の実験コピーで、停止状態のコンテナ内から実行します。

```bash
cd /workspace
python3 tools/prepare_scenes.py
```

インストール済みGazeboのサンプルから2つのworldとGUI設定を生成し、出典コメントを付けます。元の配布ファイルが変わるため、公開パッケージの一致を確かめる `verify_evidence.py` はハッシュ不一致を報告する場合があります。新しい実験には新しい `protocol.json` のシーンハッシュを記録します。

再生成したシーンでの実験には3節の起動・走行コマンドを使い、配布物の照合は変更していない元パッケージ側で行ってください。配布物照合を組み込んだ `run_headless.sh` は、配布時の構成を再現するための補助です。

## 8. 失敗した場合

| 状況 | 確認すること |
|---|---|
| `rclpy` がない | ホストのPythonではなく教材コンテナを使い、ROSのsetupをsourceしたか |
| `truth`・`odom`がない | `results/gazebo.log` と `bridge.log`、シミュレータの起動、同じコンテナ・ROS設定で実行したか |
| `Demo is already running` | その環境の `start_demo.py --stop` で終了を確認する。`processes.json` の削除で回避しない |
| 既存の結果名がある | 別の結果名を使う。元ログを上書きしない |
| 時間切れ | ログを残し、他の重い処理、描画の有無、PC負荷を確認。閾値を変えた場合は別条件として扱う |
| GUIなしは成功、表示がない | 4節の通常起動を使い、ブラウザ内のデスクトップ・ロック状態とOGRE2の表示を確認 |
| 世界の一覧を待ち続ける | 最新の起動補助がサーバーとGUIを分けて起動しているか、`results/gui.log` と `gazebo.log` を確認 |
| `/home/ubuntu/.ros/log` の権限エラー | 4節の通り実行ユーザーをそろえる。ubuntuで診断だけ行う場合は `export ROS_LOG_DIR="$(mktemp -d /tmp/pai-ros-log.XXXXXX)"` で自分用のログ先を作る |
| 動画が0バイト | `_ffmpeg.log` と `_recording.json` を確認。最新の録画処理では奇数寸法を補正し、検証に失敗した動画を `Saved` と表示しない |
| 停止を中断した | 同じコンテナで `python3 start_demo.py --stop`。起動補助は自分が開始したプロセス群だけを対象にする |

同じコンテナ内で複数の走行を同時に実行しないでください。通常のGitHub用コンテナは教材の既存コンテナとは別のComposeプロジェクトで動きます。

## レポートとの対応

2026-10-29の更新で、PDFと本書の手順を同じ公開用Composeにそろえました。PDFは実行の要点を記載し、本書にGUIなし・表示あり・録画・学習の詳細をまとめています。コマンドごとのホスト／コンテナの指定に従ってください。
