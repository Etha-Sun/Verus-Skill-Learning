"""Failed binding remains visible without actor dispatch or ordered-wave delay."""
import json
from pathlib import Path
import threading
from unittest.mock import Mock

import pytest

from skillopt_verusage.augmentation_campaign import Campaign, DEFERRED_SOURCES, EXECUTION_REVIEW
from skillopt_verusage.campaign_evidence import sha
from skillopt_verusage.guarded_deepseek import write_json


@pytest.mark.parametrize('failure', ['binding', 'schema'])
def test_validation_failure_preserves_returned_hint_and_never_dispatches_actor(tmp_path, monkeypatch, failure):
    campaign = Campaign.__new__(Campaign)
    campaign.config = {'execution_review':EXECUTION_REVIEW,'deferred_sources':DEFERRED_SOURCES}
    campaign.repo = Path(__file__).resolve().parents[2]
    campaign.prompts = campaign.repo/'skillopt-verusage/prompts'
    campaign.root = tmp_path/'run'
    campaign.lock = threading.Lock()
    campaign.progress = {'hint_rejected':0}
    campaign.refs = {'task':['final_validation']}
    campaign.traces = {'task':{}}
    campaign.hints = {}
    report = tmp_path/'report.json'
    write_json(report,{'reference_kind':'verifier_greedy_pruned','curve':[]})
    campaign.selection = {'task':{'report_binding':{'report_path':str(report),'report_sha256':sha(report)}}}
    point = {'checkpoint_id':'cp1','checkpoint_sha256':'a'*64}
    hint = {'schema_version':'hint-v1','checkpoint_sha256':'b'*64,
            'hint_text':'Establish the missing loop invariant relation.',
            'evidence_refs':[{'source_id':'final_validation','observation':'The completed proof passed.'}],
            'relation_to_original':'later_verified_repair','limitations':[]}
    if failure == 'schema':
        hint.pop('schema_version')
    campaign.teacher = Mock()
    campaign.teacher.call.return_value = (json.dumps(hint),{})
    campaign.actor = Mock()
    monkeypatch.setattr('skillopt_verusage.augmentation_campaign.packet_trace',lambda trace:{})
    with pytest.raises(RuntimeError,match='Hint needs review'):
        campaign.hint_branch({'id':'task'}, {}, point)
    directory = campaign.root/'hints/task/cp1'
    assert json.loads((directory/'hint.json').read_text()) == hint
    screen = json.loads((directory/'screen.json').read_text())
    assert screen['automatic_screen_passed'] is False
    assert screen['schema_and_evidence_valid'] is False
    assert screen['validation_error_type'] == ('AssertionError' if failure == 'binding' else 'ValidationError')
    assert campaign.progress['hint_rejected'] == 1
    assert campaign.progress['last_rejected_hint'] == 'task/cp1'
    assert 'a'*64 in campaign.teacher.call.call_args.kwargs['system']
    assert not (directory/'checkpoint.rs').exists()
    campaign.actor.assert_not_called()


def test_later_future_error_is_reported_before_first_finishes_without_next_wave():
    campaign = Campaign.__new__(Campaign)
    campaign.selection = {'task':{'selected':[1,2,3]}}
    release, noticed = threading.Event(), threading.Event()
    launched, errors = [], []
    def branch(item, bridge, point):
        launched.append(point)
        if point == 1:
            assert release.wait(5)
        else:
            raise RuntimeError('synthetic rejected hint')
    def update(**changes):
        assert changes['stop_after_wave'] is True
        assert changes['active_wave_error_type'] == 'RuntimeError'
        noticed.set()
    campaign.hint_branch, campaign.update = branch, update
    def run():
        try:
            campaign.run_forks([{'id':'task'}],{},2)
        except RuntimeError as error:
            errors.append(str(error))
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert noticed.wait(3)
        assert thread.is_alive()  # Already active work drains, not abandoned or relaunched.
        assert sorted(launched) == [1,2]
    finally:
        release.set()
        thread.join(3)
    assert not thread.is_alive()
    assert errors == ['synthetic rejected hint']
    assert sorted(launched) == [1,2]
