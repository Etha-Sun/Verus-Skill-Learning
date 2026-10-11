import hashlib
import json
from pathlib import Path

from skill_evolution_pilot.codex_runner import build_prompt
from skillopt_verusage.card_bank import build_bundle


REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / 'skillopt-verusage/skills'


def test_task_prompt_distinguishes_given_trust_from_new_bypasses():
    prompt = build_prompt()
    assert 'Never introduce assume, admit, external_body' in prompt
    assert 'Pre-existing trusted declarations in input.rs are supplied background' in prompt
    assert 'preserve their attributes, signatures, contracts, and bodies' in prompt
    assert 'call them through their existing contracts' in prompt
    assert 'not the supplied trusted background' in prompt
    assert 'Never use assume, admit, external_body' not in prompt


def test_task_prompt_prioritizes_small_diagnostic_repairs_without_forced_cards():
    prompt = build_prompt()
    assert 'Fix parse, type/mode, and scope errors before changing proof strategy' in prompt
    assert 'assert(condition);' in prompt
    assert 'Run `./tools/run_verus.sh` after edits' in prompt
    assert 'Run `./tools/run_lynette.sh` before finishing' in prompt
    assert 'card_read.py' not in prompt


def test_versioned_executive_keeps_initial_skill_unchanged():
    assert hashlib.sha256((SKILLS / 'initial.md').read_bytes()).hexdigest() == (
        '96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40'
    )
    revised = (SKILLS / 'diagnostic-first-v1.md').read_text()
    assert 'Pre-existing trusted declarations' in revised
    assert 'parse, type/mode, or scope error' in revised
    assert 'exact terms' in revised
    assert 'make the antecedent available explicitly' in revised
    assert 'card-' not in revised
    for task_id in ('aded7990', 'a23a4969', '3ce00a38', '9b9f6cce'):
        assert task_id not in revised


def test_versioned_executive_does_not_change_card_reader_or_bank(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    cards = [{'id': 'card-001', 'content': (
        '**Trigger:** A diagnostic.\n**Action:** Inspect context.\n'
        '**Why:** Existing evidence.\n**Validate:** Run both checks.\n'
        '**Avoid when:** Premises are absent.'
    )}]
    bank = tmp_path / 'bank.json'
    bank.write_text(json.dumps({'schema_version': 'stage-card-bank-v1', 'cards': cards}))
    for name, seed in (('control', 'initial.md'), ('revised', 'diagnostic-first-v1.md')):
        build_bundle(bank, SKILLS / seed, tmp_path / name, autonomous_retrieval=True,
                     index_descriptions={'card-001': 'Diagnostic routing.'})
    for name in ('cards.json', 'card_read.py'):
        assert (tmp_path / 'control' / name).read_bytes() == (tmp_path / 'revised' / name).read_bytes()
    for name in ('control', 'revised'):
        prompt = (tmp_path / name / 'SKILL.md').read_text()
        assert 'no retrieval ranking or fixed' in prompt
        assert 'Diagnostic routing.' in prompt
        assert '### When a card can help' not in prompt
