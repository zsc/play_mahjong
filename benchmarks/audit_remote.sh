#!/bin/sh
ssh -o BatchMode=yes -o ConnectTimeout=10 desk 'cd /home/zsc/play_mahjong && OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=training /home/zsc/mahjong-venv/bin/python -' <<'PY'
import glob, json, pathlib, time, random, subprocess, os
import torch
from train_ppo import load_initial_model, collect_rollouts, ppo_update

torch.set_num_threads(1)
print('REMOTE AUDIT', flush=True)
print(subprocess.check_output(['free','-h'], text=True), flush=True)
print(subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu,power.draw','--format=csv'], text=True), flush=True)
for i in (0,7,8,23):
    p=pathlib.Path(f'training/logs/generate-qualified-30k-{i}.log')
    print(str(p), p.read_text().splitlines()[-1:] if p.exists() else 'missing', flush=True)
print('Completed shards:', len(glob.glob('training/data/qualified-tenpai-v1-30k/*.npz')),
      'sidecars:', len(glob.glob('training/data/qualified-tenpai-v1-30k/*.meta.json')), flush=True)
model, checkpoint = load_initial_model(pathlib.Path('training/checkpoints/ppo-discard-closed-v6-38k.pt'), torch.device('cpu'))
model.eval()
t=time.perf_counter()
rows, outcomes, scores = collect_rollouts(model, torch.device('cpu'), 12100000, 4, 1, 20261026,
    2000, 'none', 'qualified-tenpai', 'qualified-tenpai', .99, .95)
rollout_seconds=time.perf_counter()-t
print(json.dumps({'rollout_games':4,'rows':len(rows),'rollout_seconds':rollout_seconds,
    'outcomes':outcomes,'scores':scores,'hidden':checkpoint['hidden'],
    'parameters':sum(p.numel() for p in model.parameters()),'torch':torch.__version__,
    'note':'CPU rollout during 24 active data-generation workers; not an idle-machine scaling test'}), flush=True)
for device_name in ('cpu','cuda'):
    device=torch.device(device_name)
    model,_=load_initial_model(pathlib.Path('training/checkpoints/ppo-discard-closed-v6-38k.pt'),device)
    model.train()
    optimizer=torch.optim.AdamW(model.parameters(),lr=5e-5)
    # Warm up optimizer/kernels without writing any checkpoint; benchmark only.
    ppo_update(model,optimizer,rows,device,1,512,.2,.5,.01,.5,random.Random(42))
    if device_name=='cuda':
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    t=time.perf_counter()
    metrics=ppo_update(model,optimizer,rows,device,4,512,.2,.5,.01,.5,random.Random(43))
    if device_name=='cuda': torch.cuda.synchronize()
    print(json.dumps({'update_device':device_name,'update_seconds':time.perf_counter()-t,
        'epochs':4,'minibatch':512,'samples':len(rows),'metrics':metrics,
        'peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20 if device_name=='cuda' else None}),flush=True)
PY
