"""Derive a one-vehicle scene from the installed Gazebo Fortress example."""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--engine', choices=['ogre', 'ogre2'], default='ogre')
args = parser.parse_args()
SOURCE = Path('/usr/share/ignition/ignition-gazebo6/worlds/diff_drive.sdf')
tree = ET.parse(SOURCE)
world = tree.getroot().find('world')
world.set('name', 'delivery_smoke')
world.remove(world.find("model[@name='vehicle_green']"))
robot = world.find("model[@name='vehicle_blue']")
robot.set('name', 'delivery_bot')
robot.find('pose').text = '0 0 0.325 0 0 0'
world.find('light/cast_shadows').text = 'false'
ground = world.find("model[@name='ground_plane']")
for size in ground.findall('.//plane/size'):
    size.text = '20 20'
drive = robot.find("plugin[@name='gz::sim::systems::DiffDrive']")
drive.find('odom_publish_frequency').text = '20'
ET.SubElement(drive, 'topic').text = '/cmd_vel'
ET.SubElement(drive, 'odom_topic').text = '/odom'
ET.SubElement(drive, 'frame_id').text = 'odom'
ET.SubElement(drive, 'child_frame_id').text = 'base_link'
# Dedicated model-only world pose for independent evaluation.
poses = ET.SubElement(robot, 'plugin', filename='ignition-gazebo-pose-publisher-system',
                      name='gz::sim::systems::PosePublisher')
# Fortress implementation requires both model flags for the top-level pose.
# This scene contains no nested models; only delivery_bot is emitted.
for key, value in {'publish_model_pose': 'true', 'publish_link_pose': 'false',
                   'publish_nested_model_pose': 'true', 'use_pose_vector_msg': 'false',
                   'update_frequency': '20'}.items():
    ET.SubElement(poses, key).text = value
scene = ET.SubElement(world, 'scene')
ET.SubElement(scene, 'shadows').text = 'false'
ET.SubElement(scene, 'ambient').text = '0.6 0.6 0.6 1'
ET.SubElement(scene, 'background').text = '0.85 0.9 0.95 1'
marker = ET.fromstring('''<model name="goal_marker"><static>true</static>
<pose>3 2 0.015 0 0 0</pose><link name="marker">
<visual name="visual"><geometry><cylinder><radius>0.35</radius>
<length>0.03</length></cylinder></geometry><material>
<ambient>1 0.5 0 1</ambient><diffuse>1 0.5 0 1</diffuse>
</material></visual></link></model>''')
world.append(marker)
ET.indent(tree, space='  ')
tree.write(ROOT / 'world.sdf', encoding='utf-8', xml_declaration=True)
# Gazebo's GUI config contains multiple top-level elements, not a single XML root.
gui_source = Path('/usr/share/ignition/ignition-gazebo6/gui/gui.config').read_text()
gui = ET.fromstring('<config>' + gui_source.replace('<?xml version="1.0"?>', '') + '</config>')
gui.find('dialog').set('show_again', 'false')
gui.find('window/width').text = '1000'
gui.find('window/height').text = '700'
gui.find('.//engine').text = args.engine
gui.find('.//camera_pose').text = '6 -8 7 0 0.55 2.1'
gui.find('.//background_color').text = '0.85 0.9 0.95'
gui.find('.//ambient_light').text = '0.6 0.6 0.6'
(ROOT / 'gui.config').write_text('\n'.join(ET.tostring(e, encoding='unicode') for e in gui))
(ROOT / 'scene_metadata.json').write_text(json.dumps({'render_engine': args.engine,
    'physics_step_seconds': 0.001, 'shadows': False, 'vehicles': 1,
    'evaluation_pose_frequency_hz': 20}, indent=2))
print('Prepared world.sdf and gui.config from the installed official sample.')
