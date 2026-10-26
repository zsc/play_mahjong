"""Frozen four-seat development comparisons for all-action league snapshots."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--expert',type=Path,required=True)
    p.add_argument('--updates',default='8,16,32,64')
    p.add_argument('--workers',type=int,default=24)
    p.add_argument('--seeds',type=int,default=1000)
    p.add_argument('--seed-start',type=int,default=60000000)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ['MAHJONG_FFI_LIBRARY']=str(root/'native/mahjong_ffi.so')
    destination=a.run/'development'
    destination.mkdir(exist_ok=False)
    results=[]
    deadline=time.monotonic()+7200
    for update in map(int,a.updates.split(',')):
        checkpoint=a.run/f'u{update:04d}.pt'
        while not checkpoint.exists():
            if time.monotonic()>deadline:
                raise TimeoutError(f'snapshot did not appear: {checkpoint}')
            time.sleep(10)
        output=destination/f'u{update:04d}'
        command=[sys.executable,'-u','training/arena.py','--old',str(a.expert),'--new',str(checkpoint),
                 '--output',str(output),'--seed-start',str(a.seed_start),'--seeds',str(a.seeds),
                 '--workers',str(a.workers),'--challengers','new-full,old-guard','--opponents','qualified,old-guard']
        with (destination/f'u{update:04d}.log').open('w') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
        report=json.loads((output/'summary.json').read_text())
        row={'update':update,'checkpoint':str(checkpoint),'sha256':report['new_sha256'],
             'qualified':report['summaries']['new-full-vs-qualified'],
             'direct':report['summaries']['new-full-vs-old-guard'],
             'paired_qualified':report['paired_vs_old_guard']['qualified']['new-full']}
        row['selection_score']=(row['paired_qualified']['mean']+row['direct']['score']['mean'])/2
        results.append(row)
        (destination/'summary.json').write_text(json.dumps(results,indent=2))
        print(json.dumps(row),flush=True)


if __name__=='__main__':
    main()
