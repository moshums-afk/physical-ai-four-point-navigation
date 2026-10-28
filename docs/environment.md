# 実行環境と検証範囲

## 使用環境

元の学習・走行はWindows / WSL 2 / Ubuntu-22.04 / Dockerの教材環境で行いました。学習と推論はCPUを使い、4点の録画ではGazeboのOGRE2描画を使いました。

2026-10-27に既存の実行環境から読み取った版は次の通りです。元の学習時の情報は `learned/training_metrics.json` に別途保存しています。

| 項目 | 確認値 |
|---|---|
| Python | 3.10.12 |
| NumPy | 1.24.4 |
| ROS 2 | Humble |
| Gazebo / libignition-gazebo6 | 6.16.0 / 6.16.0-2~jammy |
| ros-humble-ros-gz-bridge | 0.244.16-2jammy.20250114.164355 |
| PyTorch | パッケージ2.6.0。元の学習記録は2.6.0+cu124、計算はCPU |
| Pillow | 9.0.1 |
| matplotlib | 3.5.1（単一目標用の軌跡描画補助で使用） |
| ffmpeg | 7:4.4.2-0ubuntu0.22.04.1 |
| x11-utils | 7.7+5build2 |
| fonts-takao-gothic | 00303.01-3ubuntu1 |

## 固定した教材イメージ

`compose.yaml` は `latest` タグではなく、ローカルイメージのRepoDigestsで確認できた次の参照を使います。

```text
airobotbook/ros2-desktop-ai-robot-book-humble@sha256:b58ec74c019aacd9ce4818fa25fc5a9e0a1f22f8c9cd1f5260994bf15cd9eb63
```

CPUでの保存モデル推論に必要なNumPy、ROS Pythonパッケージ、Gazebo、ros_gz_bridgeが、このイメージから作った一時コンテナにあることを確認しました。追加学習は別途 `tools/check_environment.py --training`、録画は `--recording` で確認します。

このイメージのリモートレジストリからの新規取得、別PCでの初回インストール、異なるCPUアーキテクチャの動作は検証していません。確認済みイメージを取得できない場合は、別版へ黙って置き換えず、使用したイメージを記録して別条件として評価してください。

## 公開用の起動設定

- Composeプロジェクト名：`physical-ai-four-points`。
- GUIのブラウザ接続：`127.0.0.1:6082`。外部ネットワークへデスクトップを公開しません。
- 共有フォルダ：リポジトリのルートをコンテナの `/workspace` に対応させます。
- ROS_DOMAIN_ID：52、ROS_LOCALHOST_ONLY：1。
- `run_headless.sh` はGUIを起動しない一時コンテナでも実行できます。
- GUI・録画のコードは教材デスクトップの `DISPLAY=:0` と `/home/ubuntu/.Xauthority` を使います。これは教材イメージ内の既定配置です。

## 描画・動画編集

表示には同梱の `gui_waypoints.config` とOGRE2を使います。ホスト側のGPU・ドライバ・ソフトウェア描画の違いで描画速度は変わります。シミュレーション内の秒数、実際に待った時間、動画の長さは別々に扱ってください。

動画合成補助はffmpegの `ass` フィルタ、Pillow、日本語フォントを使います。録画画面の解像度とウィンドウ配置に合わせて、切り出し位置を確認する必要があります。2026-10-28のハンズオンでGUI表示・録画・再生を本人が確認しました。デスクトップ981×584を982×584へ余白補正し、H.264の132.136秒の録画を保存しました。動画合成補助の再実行はまだ確認していません。

実際に何を実行して確認したかは [validation.md](validation.md) に記録しています。
