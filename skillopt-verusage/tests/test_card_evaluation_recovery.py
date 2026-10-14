"""Recovery preserves unknown charges instead of zeroing interrupted calls."""
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def recovery(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/'scripts'))
    return importlib.import_module('recover_card_organization_evaluation')


def test_unknown_reservations_included_in_prior_charge(recovery):
    state = {'prior_spend_usd': 0, 'target_spend_usd': .167177296,
             'uncertain_spend_usd': 0, 'reservations': {'first': 1.83904512, 'second': 1.83904512}}
    assert recovery.inherited_charge(state) == pytest.approx(3.845267536)
    assert len(state['reservations']) == 2


def test_existing_unknown_and_prior_spend_are_not_dropped(recovery):
    state = {'prior_spend_usd': 2, 'target_spend_usd': 3,
             'uncertain_spend_usd': 4, 'reservations': {'pending': 5}}
    assert recovery.inherited_charge(state) == 14
