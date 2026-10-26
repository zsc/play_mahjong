"""Bounded SOFY full-action distillation/PPO experiment stages."""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=['probe','warm','ppo'],required=True)
    p.add_argument('--warm-checkpoint',type=Path)
    p.add_argument('--branch',type=int,choices=range(4),default=0)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ['MAHJONG_FFI_LIBRARY']=str(root/'native/mahjong_ffi.so')
    command=[sys.executable,'-u','training/league.py','--expert',str(root/'initial.bin'),'--device','cuda']
    if a.stage=='probe':
        command+=['--init',str(root/'initial.bin'),'--output',str(root/'league-probe'),
                  '--phase','distill','--updates','3','--games','128','--workers','8','--batch-size','16',
                  '--snapshot-every','1','--epochs','2','--seed-start','49000000']
    elif a.stage=='warm':
        command+=['--init',str(root/'initial.bin'),'--output',str(root/'league-warm'),
                  '--phase','distill','--updates','64','--games','1024','--workers','32','--batch-size','32',
                  '--lr','0.0003','--epochs','4','--teacher-mix','0.5','--snapshot-every','8','--seed-start','50000000']
    else:
        if a.warm_checkpoint is None:
            p.error('--warm-checkpoint required for PPO')
        lr,bc,entropy,self_play=[(3e-5,.1,.001,.25),(1e-4,.1,.003,.25),
                                (3e-5,0.,.001,.5),(1e-4,.5,.001,.25)][a.branch]
        command+=['--init',str(a.warm_checkpoint),'--output',str(root/f'league-ppo-b{a.branch}'),
                  '--phase','ppo','--updates','128','--games','2048','--workers','32','--batch-size','32',
                  '--lr',str(lr),'--teacher-bc',str(bc),'--entropy',str(entropy),'--self-play-fraction',str(self_play),
                  '--snapshot-every','16','--seed-start',str(52000000+a.branch*2000000),
                  '--seed',str(202610270+a.branch)]
    subprocess.run(command,check=True,timeout=7200)


if __name__=='__main__':
    main()
