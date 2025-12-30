import json
import tempfile
import os

from evals.evaluation import persist_confidence, add_or_update_outcome_metadata


def make_sample_outcomes(path):
    data = [{"1": {"eventName": {"0": "ConsoleLogin"}}}, {"2": {"eventName": {"0": "AccessDenied"}}}]
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def test_persist_confidence_creates_meta_and_updates_file():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'hypotheses_outcomes.json')
        make_sample_outcomes(path)
        persist_confidence('2', 0.75, 'three quarters match', outcomes_path=path)
        with open(path, 'r') as f:
            data = json.load(f)
        # find hypothesis '2'
        entry = next((it for it in data if isinstance(it, dict) and '2' in it), None)
        assert entry is not None
        assert 'meta' in entry['2']
        assert entry['2']['meta']['confidence'] == 0.75
        assert 'confidence_explanation' in entry['2']['meta']


def test_add_or_update_outcome_metadata_appends_missing():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'hypotheses_outcomes.json')
        # start empty
        with open(path, 'w') as f:
            json.dump([], f)
        add_or_update_outcome_metadata('9', {'confidence': 0.1}, outcomes_path=path)
        with open(path, 'r') as f:
            data = json.load(f)
        entry = next((it for it in data if isinstance(it, dict) and '9' in it), None)
        assert entry is not None
        assert entry['9']['meta']['confidence'] == 0.1
