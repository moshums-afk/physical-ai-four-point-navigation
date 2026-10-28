"""Verify preserved evidence, order, radii, stopping, time limits and hashes."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/'final_project/diff_drive_smoke'
sys.path.insert(0,str(CODE))
from waypoint_route import score_route

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=json.loads((ROOT/'docs/source_manifest.json').read_text(encoding='utf-8'))
    assert digest(CODE/'learned/policy.npz')==manifest['model_sha256'],'Saved model mismatch'
    for item in manifest['copied_files']:
        p=ROOT/item['path']
        revision=manifest.get('revisions',{}).get(item['path'])
        expected=item['packaged_sha256']
        if revision:
            assert revision['base_packaged_sha256']==expected
            expected=revision['sha256']
        assert digest(p)==expected,f'Changed packaged file: {item["path"]}'
        if not item['byte_identical']:
            assert p.suffix in ('.sdf','.config')
            restored=re.sub(r'<!-- Modified for this four-point project.*?-->\n','',p.read_text(encoding='utf-8'),count=1,flags=re.S)
            assert hashlib.sha256(restored.encode()).hexdigest()==item['source_sha256'],f'Non-comment change: {p.name}'
    results=[]
    for folder in sorted((ROOT/'evidence').glob('four_points_*')):
        if not folder.is_dir(): continue
        data=json.loads((folder/'summary.json').read_text())
        p,r=data['protocol'],data['result']
        assert p==json.loads((folder/'protocol.json').read_text())
        assert r['visits']==json.loads((folder/'visits.json').read_text())
        assert p['model_sha256']==manifest['model_sha256']
        with (folder/'trajectory.csv').open(newline='') as f: rows=list(csv.DictReader(f))
        for v in r['visits']:
            goal=p['route']['goals'][v['point']-1]
            row=next(x for x in rows if int(x['accepted_point'])==v['point'])
            assert abs(math.dist(v['true_xy'],goal)-v['true_distance_m'])<1e-8
            assert abs(float(row['sim'])-v['sim_seconds'])<1e-8
        if folder.name.endswith('v2'):
            assert p['route']['goal_reference']=='wheel_axle_center'
            last=rows[-1]
            xy=(float(last['x_true']),float(last['y_true']))
            speed=(float(last['odom_v']),float(last['odom_w']))
            first_stop=next(x for x in rows if x['phase']=='stop')
            hold=float(last['sim'])-float(first_stop['sim'])
            success,distance=score_route(r['visits'],xy,p['route']['goals'][-1],speed,
                                          hold>=p['criteria']['stop_hold_sim_seconds'],r['error'])
            assert success and r['success'] and r['hold_complete']
            assert abs(distance-r['final_true_distance_m'])<.002
            assert r['sim_seconds']<=p['criteria']['max_sim_seconds']
            assert r['wall_seconds']<=p['criteria']['max_wall_seconds']
            assert all(v['estimated_distance_m']<=p['criteria']['switch_radius_m'] for v in r['visits'])
        else:
            assert not r['success'] and r['error']=='Simulation time limit'
            assert [v['point'] for v in r['visits']]==[1]
        results.append({'run':folder.name,'success':r['success'],
                        'visits':[v['point'] for v in r['visits']],
                        'final_distance_m':r['final_true_distance_m']})
    assert len(results)==3
    print(json.dumps({'verified':True,'copied_files':len(manifest['copied_files']),
                      'model_sha256':manifest['model_sha256'],'runs':results},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
