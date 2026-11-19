"""Internal evidence gate. Existence/hash of evidence is not regulatory approval."""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = {
    'legal_owner', 'intended_use_classification', 'market_authorizations',
    'b4d_integration_rights', 'code_and_corpus_rights', 'dependency_review',
    'geometry_validation', 'isolated_execution', 'privacy_contracts',
    'subscription_backend', 'independent_security_review', 'backup_restore',
    'windows_signed_test', 'macos_signed_notarized_test', 'release_operations',
}


def check(data, root):
    errors = []
    if not isinstance(data, dict) or not isinstance(data.get('requirements'), list):
        return ['Formato de registro no válido']
    entries = data['requirements']
    ids = [entry.get('id') for entry in entries if isinstance(entry, dict)]
    if len(ids) != len(entries) or len(set(ids)) != len(ids):
        errors.append('Requisitos inválidos o duplicados')
    for missing in sorted(REQUIRED - set(ids)):
        errors.append(missing + ': requisito ausente')
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get('id', '?'))
        if entry.get('status') != 'approved':
            errors.append(label + ': pendiente')
            continue
        if not entry.get('reviewer') or not entry.get('reviewed_at'):
            errors.append(label + ': falta responsable/fecha de revisión')
        evidence = entry.get('evidence', {})
        relative = evidence.get('file') if isinstance(evidence, dict) else None
        if not isinstance(relative, str) or not relative:
            errors.append(label + ': falta evidencia')
            continue
        file = (root / relative).resolve()
        if not file.is_relative_to(root.resolve()) or not file.is_file():
            errors.append(label + ': evidencia fuera de carpeta o inexistente')
            continue
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if evidence.get('sha256') != digest:
            errors.append(label + ': hash de evidencia incorrecto')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, default=Path(__file__).with_name('release-readiness.json'))
    parser.add_argument('--evidence-root', type=Path, default=Path('release-evidence'))
    args = parser.parse_args()
    errors = check(json.loads(args.record.read_text(encoding='utf-8-sig')), args.evidence_root)
    print(json.dumps({'status': 'BLOCKED_FOR_SALE' if errors else 'EVIDENCE_RECORDED_REQUIRES_RELEASE_APPROVAL', 'pending': errors}, ensure_ascii=False, indent=2))
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
