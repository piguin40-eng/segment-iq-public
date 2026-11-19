import hashlib
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('readiness', Path(__file__).with_name('check_readiness.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_missing_and_pending_requirements_block(tmp_path):
    assert gate.check({'requirements': []}, tmp_path)
    assert gate.check({'requirements': [{'id': key, 'status': 'pending'} for key in gate.REQUIRED]}, tmp_path)


def test_approval_needs_real_contained_matching_evidence(tmp_path):
    evidence = tmp_path / 'review.txt'
    evidence.write_text('Synthetic test evidence; not approval')
    entries = [{'id': key, 'status': 'approved', 'reviewer': 'Test reviewer', 'reviewed_at': '2026-09-11',
                'evidence': {'file': 'review.txt', 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}} for key in gate.REQUIRED]
    assert not gate.check({'requirements': entries}, tmp_path)
    entries[0]['evidence']['file'] = '../escape.txt'
    assert gate.check({'requirements': entries}, tmp_path)
    entries[0]['evidence']['file'] = 'review.txt'
    evidence.write_text('Tampered')
    assert gate.check({'requirements': entries}, tmp_path)


def test_duplicate_requirements_cannot_replace_missing_requirement(tmp_path):
    assert gate.check({'requirements': [{'id': 'legal_owner', 'status': 'approved'}] * len(gate.REQUIRED)}, tmp_path)
