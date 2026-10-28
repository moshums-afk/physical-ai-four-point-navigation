"""Check the exact features required for the selected workflow. No robot motion."""
import argparse
import importlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def command(argv):
    try:
        r = subprocess.run(argv, text=True, capture_output=True, timeout=25)
        return {'exit_code':r.returncode, 'stdout':r.stdout.strip(), 'stderr':r.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'exit_code':-1,'error':str(exc)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--training',action='store_true')
    parser.add_argument('--recording',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report={'python':platform.python_version(),'machine':platform.machine(),
            'ROS_DISTRO':os.environ.get('ROS_DISTRO'),'modules':{},'checks':{},'missing':[]}
    modules=['numpy','rclpy','geometry_msgs.msg','nav_msgs.msg','rosgraph_msgs.msg']
    if args.training: modules+=['torch']
    if args.recording: modules+=['PIL']
    for name in modules:
        try:
            m=importlib.import_module(name)
            report['modules'][name]={'ok':True,'version':getattr(m,'__version__',None)}
        except ImportError:
            report['modules'][name]={'ok':False}
            report['missing'].append(name)
    for name in ['ros2','ign']+(['ffmpeg','ffprobe','xdpyinfo'] if args.recording else []):
        report['checks'][name]=bool(shutil.which(name))
        if not report['checks'][name]: report['missing'].append(name)
    report['gazebo']=command(['ign','gazebo','--versions'])
    report['bridge']=command(['ros2','pkg','prefix','ros_gz_bridge'])
    for name in ['gazebo','bridge']:
        if report[name]['exit_code']!=0: report['missing'].append(name)
    for name in ['world.sdf','world_waypoints.sdf','gui.config','gui_waypoints.config','learned/policy.npz']:
        ok=(ROOT/'final_project/diff_drive_smoke'/name).is_file()
        report['checks'][name]=ok
        if not ok: report['missing'].append(name)
    if args.recording:
        env=dict(os.environ,DISPLAY=':0',XAUTHORITY='/home/ubuntu/.Xauthority')
        try:
            r=subprocess.run(['xdpyinfo'],env=env,capture_output=True,timeout=15)
            report['checks']['display']=r.returncode==0
        except (OSError,subprocess.TimeoutExpired):
            report['checks']['display']=False
        font=Path('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf')
        report['checks']['japanese_font']=font.is_file()
        report['checks']['ffmpeg_ass_filter']=' ass ' in command(['ffmpeg','-hide_banner','-filters']).get('stdout','')
        for name in ['display','japanese_font','ffmpeg_ass_filter']:
            if not report['checks'][name]: report['missing'].append(name)
    report['ok']=not report['missing']
    report['note']='Dependency check only; see a run summary for Gazebo task completion.'
    payload=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as f: f.write(payload)
    print(payload)
    return 0 if report['ok'] else 1

if __name__=='__main__':
    raise SystemExit(main())
