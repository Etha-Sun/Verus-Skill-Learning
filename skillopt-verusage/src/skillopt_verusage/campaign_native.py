"""Preserve native SkillOpt learning algorithms; replace only paid transport."""
from __future__ import annotations

import math
import os
import random
import json
from pathlib import Path

from skillopt_verusage.codex_reoptimize import _candidate_audit
from skillopt_verusage.guarded_deepseek import write_json


def reject_fallback(patch):
    reasoning = patch.get('reasoning','')
    if reasoning.startswith(('fallback concatenation','fallback: failure first')) or '[fallback truncated ' in reasoning:
        raise RuntimeError('Native aggregation/ranking fallback is not accepted')


def learn_native(results, predictions: Path, seed: Path, root: Path, reflect_client, final_client):
    from skillopt.gradient import reflect, aggregate
    from skillopt.optimizer import clip
    from skillopt.optimizer.skill import apply_patch_with_report
    from skillopt.engine.trainer import _normalise_patches

    os.environ.pop("SKILLOPT_PATH_REFERENCES", None)
    original = [reflect.chat_optimizer, aggregate.chat_optimizer, clip.chat_optimizer]
    try:
        reflect.chat_optimizer = reflect_client.optimizer
        aggregate.chat_optimizer = final_client.optimizer
        clip.chat_optimizer = final_client.optimizer
        skill = seed.read_text()
        root.mkdir(parents=True, exist_ok=True)
        patches = reflect.run_minibatch_reflect(results,skill,str(predictions),str(root/"patches"),
                    workers=2,failure_only=False,minibatch_size=8,edit_budget=4,
                    random_seed=20261002,skill_aware_reflection=False)
        expected = sum(math.ceil(sum(bool(r["hard"])==v for r in results)/8) for v in (True,False))
        if reflect_client.errors or len(patches)!=expected:
            raise RuntimeError("Native reflection incomplete: no fallback or source omission permitted")
        coverage = []
        for kind,hard,offset in (("fail",False,0),("succ",True,1)):
            group = [r for r in results if bool(r["hard"])==hard]
            random.Random(20261002+offset).shuffle(group)
            for index in range(0,len(group),8):
                path = root/"patches"/f"minibatch_{kind}_{index//8:03d}.json"
                patch = json.loads(path.read_text())
                patch["batch_size"] = len(group[index:index+8])
                patch["task_ids"] = [r["id"] for r in group[index:index+8]]
                coverage.append(patch)
        if {ident for p in coverage for ident in p["task_ids"]}!={r["id"] for r in results}:
            raise RuntimeError("Native source coverage mismatch")
        patches = coverage
        # as_completed is not a method hyperparameter; stabilize merge order.
        patches = sorted(patches,key=lambda p:(p.get("source_type", ""),str(p.get("task_ids",p))))
        failure,success = _normalise_patches(patches,"patch")
        merged = aggregate.merge_patches(skill,failure,success,batch_size=8,workers=2)
        reject_fallback(merged)
        ranked = clip.rank_and_select(skill,merged,max_edits=4)
        reject_fallback(ranked)
        candidate,report = apply_patch_with_report(skill,ranked)
        if final_client.errors:
            raise RuntimeError("Native aggregation/ranking failed; fallback is not accepted")
        # Unmodified native skills may explain generic Verus syntax. The prose-only
        # constraint belongs to cards/Codex distillation, not this native control.
        audit = _candidate_audit(skill,candidate,ranked,report,prose_only=False)
        # A legitimate no-update is an outcome, not permission to regenerate.
        audit = [x for x in audit if x != "candidate is identical to the seed skill"]
        if audit:
            raise RuntimeError("Native candidate audit: " + "; ".join(audit))
        write_json(root/"learning.json",{"source_count":len(results),"patches":patches,
                "merged":merged,"ranked":ranked,"apply_report":report,"audit":audit,
                "no_update":candidate==skill,"native_validation_gate":"pending common held-out evaluation"})
        target = root/"SKILL.md"
        target.write_text(candidate)
        return target
    finally:
        reflect.chat_optimizer,aggregate.chat_optimizer,clip.chat_optimizer = original
