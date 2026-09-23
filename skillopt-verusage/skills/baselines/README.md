# SkillOpt baseline skill references

`train40-stage1-skill-001.md` is the user-supplied skill produced by the first
SkillOpt analysis over the ordinary train-40 trajectories. It is a comparison
reference for the fork-packet augmentation diagnostic. It is not used as the
seed skill for that diagnostic; `../initial.md` remains the frozen seed.

After the augmented candidate is generated, compare the two skills using
evidence from the fork packets:

- retained, removed, and newly added guidance;
- observable trigger or proof stage;
- recommended action;
- verifier-grounded validation step;
- failure boundary or avoid-when condition;
- supporting and contradicting branches;
- whether an apparent addition is task-specific or reusable.

Textual difference alone is not evidence of improved solved rate or token
efficiency. Those claims require the later matched baseline and held-out gate.
