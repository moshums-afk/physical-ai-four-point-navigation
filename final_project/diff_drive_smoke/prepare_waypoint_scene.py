"""Make a separate four-point scene from the preserved single-goal world.

Run with start_demo.py --waypoints. Markers have visuals only, no collision.
Number glyphs use simple boxes, so no fonts or external textures are needed.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from waypoint_route import ROUTE, COLORS

ROOT = Path(__file__).resolve().parent
DIGITS = {'1': ['010', '110', '010', '010', '111'],
          '2': ['111', '001', '111', '100', '111'],
          '3': ['111', '001', '111', '001', '111'],
          '4': ['101', '101', '111', '001', '001']}


def material(visual, color):
    mat = ET.SubElement(visual, 'material')
    for name in ('ambient', 'diffuse'):
        ET.SubElement(mat, name).text = color


def main():
    tree = ET.parse(ROOT / 'world.sdf')
    world = tree.getroot().find('world')
    for old in list(world.findall('model')):
        if old.get('name') == 'goal_marker' or old.get('name', '').startswith('waypoint_'):
            world.remove(old)
    robot = world.find("model[@name='delivery_bot']")
    wheels = [list(map(float, robot.find(f"link[@name='{side}_wheel']/pose").text.split()[:2]))
              for side in ('left', 'right')]
    ax, ay = [sum(w[i] for w in wheels)/2 for i in (0, 1)]
    chassis = robot.find("link[@name='chassis']")
    cx, cy, cz = map(float, chassis.find('pose').text.split()[:3])
    refvis = ET.SubElement(chassis, 'visual', name='white_reference_point')
    ET.SubElement(refvis, 'pose').text = f'{ax-cx} {ay-cy} {0.52-cz} 0 0 0'
    ball = ET.SubElement(ET.SubElement(refvis, 'geometry'), 'sphere')
    ET.SubElement(ball, 'radius').text = '0.075'
    material(refvis, '1 1 1 1')
    for number, ((x, y), color) in enumerate(zip(ROUTE['goals'], COLORS), 1):
        model = ET.SubElement(world, 'model', name=f'waypoint_{number}')
        ET.SubElement(model, 'static').text = 'true'
        ET.SubElement(model, 'pose').text = f'{x} {y} 0 0 0 0'
        link = ET.SubElement(model, 'link', name='marker')
        visual = ET.SubElement(link, 'visual', name='disc')
        ET.SubElement(visual, 'pose').text = '0 0 0.012 0 0 0'
        cyl = ET.SubElement(ET.SubElement(visual, 'geometry'), 'cylinder')
        ET.SubElement(cyl, 'radius').text = '0.25'
        ET.SubElement(cyl, 'length').text = '0.02'
        material(visual, color)
        # A separate large numeral beside the disk remains visible near the robot.
        for row, bits in enumerate(DIGITS[str(number)]):
            for col, bit in enumerate(bits):
                if bit != '1':
                    continue
                pixel = ET.SubElement(link, 'visual', name=f'digit_{row}_{col}')
                ET.SubElement(pixel, 'pose').text = f'{0.68+(col-1)*0.09} {(2-row)*0.09} 0.025 0 0 0'
                box = ET.SubElement(ET.SubElement(pixel, 'geometry'), 'box')
                ET.SubElement(box, 'size').text = '0.085 0.085 0.025'
                material(pixel, color)
    ET.indent(tree, space='  ')
    tree.write(ROOT / 'world_waypoints.sdf', encoding='utf-8', xml_declaration=True)
    source = (ROOT / 'gui.config').read_text()
    gui = ET.fromstring('<config>' + source.replace('<?xml version="1.0"?>', '') + '</config>')
    gui.find('.//engine').text = 'ogre2'
    gui.find('.//camera_pose').text = '3 -3 5 0 0.78 2.034'
    gui.find('window/width').text = '1280'
    gui.find('window/height').text = '900'
    # Keep a large uncluttered view for recording.
    keep = {'MinimalScene', 'GzSceneManager', 'InteractiveViewControl', 'CameraTracking',
            'MarkerManager', 'WorldControl', 'WorldStats'}
    for plugin in list(gui.findall('plugin')):
        if plugin.get('filename') not in keep:
            gui.remove(plugin)
    (ROOT / 'gui_waypoints.config').write_text('\n'.join(ET.tostring(e, encoding='unicode') for e in gui))
    (ROOT / 'waypoint_scene_metadata.json').write_text(json.dumps({
        'render_engine': 'ogre2', 'route': ROUTE, 'marker_radius_m': 0.25,
        'marker_collision': False, 'source_world': 'world.sdf'}, indent=2))
    print('Prepared separate four-point world and GUI.')


if __name__ == '__main__':
    main()
