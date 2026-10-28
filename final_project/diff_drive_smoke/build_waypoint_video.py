"""Compose a factual submission video from Gazebo footage and its own run log.

Run inside the lecture container (ffmpeg, Pillow, Japanese fonts installed).
All telemetry comes from the recorded trial; no simulated replacement footage.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'
BG, PANEL, INK, MUTED = '#101c30', '#1c2c43', '#f2f6fc', '#a9b9cf'
COLORS = ['#39badd', '#f1c640', '#b38bdf', '#50cea1']
W, H = 1920, 1080


def text(draw, xy, value, size=32, fill=INK):
    draw.text(xy, value, font=ImageFont.truetype(FONT, size), fill=fill)


def mapping(x, y):
    return 1460 + x*195, 530 - y*105


def route_map(draw, goals):
    points = [mapping(0.5542825, 0)] + [mapping(*g) for g in goals]
    for p, q in zip(points, points[1:]):
        draw.line([p, q], fill='#7187a4', width=4)
        dx, dy = q[0]-p[0], q[1]-p[1]
        length = math.hypot(dx, dy)
        ux, uy = dx/length, dy/length
        mx, my = (p[0]+q[0])/2, (p[1]+q[1])/2
        draw.polygon([(mx+ux*10, my+uy*10),
                      (mx-ux*8-uy*7, my-uy*8+ux*7),
                      (mx-ux*8+uy*7, my-uy*8-ux*7)], fill='#7187a4')
    for n, (p, color) in enumerate(zip(points[1:], COLORS), 1):
        draw.ellipse((p[0]-23, p[1]-23, p[0]+23, p[1]+23), fill=color)
        text(draw, (p[0]-10, p[1]-20), str(n), 32, '#101c30')
    draw.ellipse((points[0][0]-6, points[0][1]-6, points[0][0]+6, points[0][1]+6), fill=INK)
    text(draw, (points[0][0]-42, points[0][1]+25), 'START', 23, MUTED)


def timecode(t):
    cs = max(0, round(t*100))
    return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('recording')
    parser.add_argument('--trim-start', type=float, help='Verified video time of motion start')
    parser.add_argument('--speed', type=int, choices=[1, 2], default=1)
    parser.add_argument('--output-name', default='four_points_submission_v1')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    run = ROOT / 'results' / args.recording
    result = json.loads((run / 'summary.json').read_text())['result']
    if not result['success']:
        raise SystemExit('Only a successfully evaluated recording can be composed')
    recording = json.loads((ROOT / 'results' / (args.recording+'_recording.json')).read_text())
    video = ROOT / 'results' / (args.recording+'.mp4')
    out = ROOT / 'results' / args.output_name
    out.mkdir(exist_ok=True)
    final = out / 'submission.mp4'
    if final.exists():
        raise SystemExit('Existing final video preserved; use another output name')
    with (run / 'trajectory.csv').open() as f:
        rows = list(csv.DictReader(f))
    offset = result['motion_start_unix']-recording['capture_launch_unix']
    if args.trim_start is not None:
        offset = args.trim_start
    # A small tail includes the confirmed stop; title/result cards are separate.
    motion_duration = float(rows[-1]['wall'])+0.5
    main_duration = motion_duration/args.speed
    intro, outro = 5.0, max(6.0, 65.0-5.0-main_duration)
    total = intro+main_duration+outro
    if not 60 <= total <= 180:
        raise SystemExit(f'Expected duration {total:.1f}s outside submission limits')

    base = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(base)
    text(d, (48, 30), '4つの目標を、順番に。', 52)
    text(d, (50, 96), '学習済みモデルで前進速度と旋回速度を決定', 26, MUTED)
    d.rounded_rectangle((1360, 145, 1872, 988), radius=24, fill=PANEL)
    text(d, (1400, 166), '目標の順序', 28)
    route_map(d, result['route']['goals'])
    text(d, (1400, 592), '走行ログの表示', 25, MUTED)
    text(d, (1400, 660), 'AIへの入力', 25, '#64d8df')
    text(d, (1400, 800), 'AIからの出力', 25, '#64d8df')
    text(d, (50, 1012), '白点＝車輪軸中央。目標から20cm以内で次の点へ切り替え、4点目で停止。', 25, MUTED)
    text(d, (1410, 1012), '録画を2倍速で再生' if args.speed == 2 else '録画を等速で再生', 25, '#64d8df')
    base.save(out / 'background.png')

    # Intro: explain the learned part without assigning sequencing to the AI.
    title = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(title)
    text(d, (110, 110), 'PHYSICAL AI / ROS 2 + GAZEBO', 29, '#64d8df')
    text(d, (110, 220), '4地点を順に巡り、最後に止まる', 64)
    text(d, (110, 335), 'PyTorchで学習した小さなニューラルネットワークを使用', 38, MUTED)
    for x, label, lines in [(110, '入力', ['目標までの距離', '目標方向との角度差']),
                            (710, '学習済みモデル', ['ルールを教師に模倣学習', '24,000組の状態・速度']),
                            (1310, '出力', ['前進速度［m/s］', '旋回速度［rad/s］'])]:
        d.rounded_rectangle((x, 485, x+500, 785), radius=24, fill=PANEL)
        text(d, (x+35, 515), label, 33, '#64d8df')
        for i, line in enumerate(lines):
            text(d, (x+35, 605+i*66), line, 31)
    text(d, (110, 895), '目標の順序管理と停止判定は通常のプログラムが担当します。', 34, MUTED)
    title.save(out / 'intro.png')

    end = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(end)
    text(d, (110, 100), 'RESULT / この録画の実測結果', 30, '#64d8df')
    text(d, (110, 205), '1 → 2 → 3 → 4　順次到達・停止', 62)
    visits = result['visits']
    for i, visit in enumerate(visits):
        x = 110+i*440
        d.rounded_rectangle((x, 380, x+390, 590), radius=22, fill=PANEL)
        text(d, (x+30, 405), f'目標 {i+1}', 31, COLORS[i])
        text(d, (x+30, 478), f"{visit['true_distance_m']*100:.1f} cm", 53)
    text(d, (110, 625), '上段：各目標への到達判定時の距離（基準は車輪軸中央）', 31, MUTED)
    text(d, (110, 715), f"最終停止後の距離：{result['final_true_distance_m']*100:.1f} cm　／　停止速度：0 m/s・0 rad/s", 38)
    text(d, (110, 795), f"走行・停止確認：実時間 {result['wall_seconds']:.1f} 秒 ／ シミュレーション {result['sim_seconds']:.1f} 秒", 34, MUTED)
    text(d, (110, 903), '工夫：制御と評価の基準を車輪軸中央に統一。走行中は車輪の位置推定を使用。', 32)
    text(d, (110, 970), '障害物のない1コースで確認。今回の映像は実機での性能を示すものではありません。', 27, MUTED)
    end.save(out / 'outro.png')

    events = []
    def event(start, stop, x, y, value, size=30, color='&H00FFFFFF&', layer=2):
        if stop <= start:
            return
        tag = f'{{\\an7\\pos({x:.0f},{y:.0f})\\fs{size}\\c{color}}}'
        events.append(f'Dialogue: {layer},{timecode(start)},{timecode(stop)},Main,,0,0,0,,{tag}{value}')

    # Sample displayed values at 5 Hz of video time; preserve actual units even at 2x.
    selected = []
    for row in rows:
        if not selected or float(row['wall'])-float(selected[-1]['wall']) >= 0.2*args.speed:
            selected.append(row)
    for i, row in enumerate(selected):
        start = intro+float(row['wall'])/args.speed
        stop = intro+float(selected[i+1]['wall'])/args.speed if i+1 < len(selected) else intro+main_duration
        target = int(row['target'])
        status = '4点到達 / 停止確認' if row['phase'] == 'stop' else f'目標 {target} へ移動中'
        event(start, stop, 1400, 625, status, 31)
        event(start, stop, 1400, 705, f"距離     {float(row['distance_est']):.2f} m", 31)
        event(start, stop, 1400, 750, f"方角差  {math.degrees(float(row['bearing_error'])):+.0f}°", 31)
        event(start, stop, 1400, 845, f"前進     {float(row['cmd_v']):.2f} m/s", 31)
        event(start, stop, 1400, 890, f"旋回     {float(row['cmd_w']):+.2f} rad/s", 31)
        x, y = mapping(float(row['x_true']), float(row['y_true']))
        # A small outlined dot marks the measured axle position on the route map.
        tag = f'{{\\an5\\pos({x:.1f},{y:.1f})\\fs30\\bord2\\c&H00FFFFFF&\\3c&H00301C10&}}●'
        events.append(f'Dialogue: 4,{timecode(start)},{timecode(stop)},Main,,0,0,0,,{tag}')
    ass = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n'
           '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
           'Style: Main,TakaoPGothic,30,&H00FFFFFF,&H00FFFFFF,&H00101C30,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n'
           '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n' + '\n'.join(events))
    (out / 'telemetry.ass').write_text(ass, encoding='utf-8')
    info = {'source_recording': args.recording, 'source_summary': str(run/'summary.json'),
            'verified_motion_offset_s': offset, 'playback_speed': args.speed,
            'intro_s': intro, 'main_s': main_duration, 'outro_s': outro, 'expected_total_s': total,
            'source_crop': [250, 300, 800, 530], 'no_external_upload': True}
    (out / 'edit_manifest.json').write_text(json.dumps(info, indent=2))
    filters = (f'[0:v]trim=start={offset}:duration={motion_duration},setpts=(PTS-STARTPTS)/{args.speed},'
               'crop=800:530:250:300,scale=1280:848:flags=lanczos,setsar=1,fps=15[v];'
               f'[1:v][v]overlay=48:140:shortest=1,trim=duration={main_duration},setpts=PTS-STARTPTS[main];'
               f'[2:v]trim=duration={intro},setpts=PTS-STARTPTS,setsar=1[i];'
               f'[3:v]trim=duration={outro},setpts=PTS-STARTPTS,setsar=1[o];'
               '[i][main][o]concat=n=3:v=1:a=0,ass=telemetry.ass,format=yuv420p[final]')
    (out / 'filter.txt').write_text(filters)
    print(json.dumps(info), flush=True)
    if args.prepare_only:
        return
    subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'warning', '-threads', '1',
                    '-i', str(video), '-loop', '1', '-framerate', '15', '-i', 'background.png',
                    '-loop', '1', '-framerate', '15', '-i', 'intro.png',
                    '-loop', '1', '-framerate', '15', '-i', 'outro.png',
                    '-filter_complex_threads', '1', '-filter_complex_script', 'filter.txt',
                    '-map', '[final]', '-an', '-t', str(total), '-c:v', 'libx264',
                    '-preset', 'veryfast', '-crf', '20', '-threads', '2',
                    '-movflags', '+faststart', str(final)], cwd=out, check=True)
    print('SAVED', final, flush=True)


if __name__ == '__main__':
    main()
