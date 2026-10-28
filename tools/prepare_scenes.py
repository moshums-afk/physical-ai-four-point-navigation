"""Optionally regenerate scenes from installed Gazebo samples and retain attribution."""
from pathlib import Path
import subprocess
import sys

CODE=Path(__file__).resolve().parents[1]/'final_project/diff_drive_smoke'
NOTICE=('<!-- Modified for this four-point project from Gazebo gz-sim (ign-gazebo6).\n'
        '     Vehicle reduction, markers, ROS topics, pose publication and/or GUI settings changed.\n'
        '     Upstream Apache-2.0; see THIRD_PARTY_NOTICES.md and LICENSES/gazebo-Apache-2.0.txt. -->\n')

def main():
    subprocess.run([sys.executable,str(CODE/'prepare_scene.py'),'--engine','ogre2'],check=True)
    subprocess.run([sys.executable,str(CODE/'prepare_waypoint_scene.py')],check=True)
    for name in ['world.sdf','world_waypoints.sdf','gui.config','gui_waypoints.config']:
        p=CODE/name
        s=p.read_text()
        if s.startswith('<?xml'):
            at=s.index('?>')+2
            s=s[:at]+'\n'+NOTICE+s[at:].lstrip('\n')
        else: s=NOTICE+s
        p.write_text(s,encoding='utf-8')
    print('Scenes regenerated. Their hashes may differ from the packaged/recorded scenes.')
    print('Use a separate experiment copy; verify_evidence checks the original package hashes.')

if __name__=='__main__':
    main()
