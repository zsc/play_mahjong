import copy
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from league import finish_trajectories
from mahjong_ai.engine import EngineError, MahjongEngine
from mahjong_ai.features import action_mask


def request(game, decision=None, action=None):
    return {"game":game,"max_steps":2000,"action_id":action,
            "seat":decision["actor"] if decision else None,
            "revision":decision["revision"] if decision else None}


def test_full_decision_batch_matches_reference_and_preserves_choices():
    phases=set()
    with MahjongEngine() as engine:
        for seed in range(51000100,51000104):
            reference=engine.new_game(seed)
            batched=engine.new_game(seed)
            response=engine.decision_batch([request(batched)])[0]
            while "outcome" not in response:
                actor=engine.actor(reference)
                observation,_=engine.observe(reference,actor)
                while len(observation["legal_action_ids"]) == 1:
                    engine.step(reference,actor,observation["legal_action_ids"][0])
                    actor=engine.actor(reference)
                    observation,_=engine.observe(reference,actor)
                assert response["actor"] == actor
                assert response["observation"] == observation
                assert action_mask(observation).sum()==len(observation["legal_action_ids"])
                phases.add(observation["phase"]["kind"])
                action=engine.heuristic_action(reference,actor,"qualified-tenpai")
                assert action==response["teacher_action"]
                engine.step(reference,actor,action)
                response=engine.decision_batch([request(batched,response,action)])[0]
            while engine.actor(reference) is not None:
                actor=engine.actor(reference)
                legal=engine.legal_actions(reference,actor)
                assert len(legal)==1
                engine.step(reference,actor,legal[0])
            assert engine.observe(reference,0)[0]==engine.observe(batched,0)[0]
            engine.validate(batched)
    assert {"discard","response","flower"} <= phases


def test_full_batch_invalid_action_is_atomic():
    with MahjongEngine() as engine:
        games=[engine.new_game(s) for s in [51000200,51000201]]
        states=engine.decision_batch([request(g) for g in games])
        before=[engine.observe(g,s["actor"])[0] for g,s in zip(games,states)]
        with pytest.raises(EngineError):
            engine.decision_batch([request(games[0],states[0],states[0]["teacher_action"]),request(games[1],states[1],999)])
        assert before==[engine.observe(g,s["actor"])[0] for g,s in zip(games,states)]
        stale=request(games[0],states[0],states[0]["teacher_action"])
        stale["revision"]-=1
        with pytest.raises(EngineError,match="stale"):
            engine.decision_batch([stale])


def test_terminal_rewards_do_not_cross_players():
    row={"reward":0.,"value":0.}
    trajectories=[[copy.copy(row),copy.copy(row)],[copy.copy(row)],[],[]]
    rows=finish_trajectories(trajectories,{"deltas":[64,-128,32,32]},1.,.95)
    assert [r["reward"] for r in rows]==[0.,1.,-2.]
    assert [r["return"] for r in rows]==pytest.approx([.95,1.,-2.])


def test_league_resume_includes_frozen_pool_and_matches_weights(tmp_path):
    root=Path(__file__).resolve().parents[2]
    from model import PolicyValueNet
    torch.manual_seed(42)
    model=PolicyValueNet(hidden=32)
    initial=tmp_path/'initial.pt'
    torch.save({"format_version":1,"ruleset_id":"mcr-wmo2006-stage1","observation_version":1,
                "feature_encoding_version":6,"action_catalog_version":1,"feature_size":771,
                "action_count":122,"hidden":32,"model":model.state_dict()},initial)
    command=[sys.executable,str(root/'training/league.py')]
    full=tmp_path/'full'
    env=os.environ|{"OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1"}
    subprocess.run(command+["--init",str(initial),"--expert",str(initial),"--output",str(full),
        "--updates","2","--games","4","--workers","1","--batch-size","4","--epochs","1",
        "--snapshot-every","1","--device","cpu","--seed-start","51000300"],env=env,check=True,capture_output=True)
    resumed=tmp_path/'resumed'
    subprocess.run(command+["--resume",str(full/'u0001.pt'),"--expert",str(initial),"--output",str(resumed),
        "--updates","2","--device","cpu"],env=env,check=True,capture_output=True)
    a,b=[torch.load(p/'latest.pt',weights_only=True) for p in [full,resumed]]
    for key,value in a['model'].items():
        assert torch.equal(value,b['model'][key]),key
    assert all(np.isfinite(row['policy_loss']) for row in a['history'])
    assert a['history'][1]['opponent_pool']==b['history'][1]['opponent_pool']
