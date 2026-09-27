from __future__ import annotations

import ast
import asyncio
import copy
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import two_agent_service_transaction_demo as demo
from coin.disposable_offline_transfer_demo import (
    _open_ledger,
    _public_key_hex,
    build_signed_transfer,
    public_identity,
)


def _keys():
    return Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()


def _base_artifacts(tmp_path):
    payer, provider, wrong = _keys()
    payer_id = public_identity(_public_key_hex(payer))
    provider_id = public_identity(_public_key_hex(provider))
    ledger = _open_ledger(str(tmp_path))
    ledger.balances[payer_id] = 100
    ledger.balances[provider_id] = 0
    request = demo.build_service_request(payer, provider_identity=provider_id, input_text='one two two.')
    quote = demo.build_service_quote(provider, request=request)
    tx = build_signed_transfer(payer, receiver=provider_id, amount=28, timestamp=demo.DEMO_TIMESTAMP, nonce=77)
    auth = demo.build_payment_authorization(payer, request=request, quote=quote, payment_tx=tx)
    return payer, provider, wrong, ledger, request, quote, tx, auth


def test_end_to_end_transaction_has_actual_payment_work_and_receipt():
    result = demo.execute_two_agent_service_transaction('L28 enables machine payments between autonomous systems.')
    assert result['request_created'] is True
    assert result['quote_created'] is True
    assert result['quoted_amount'] == 28
    assert len(result['payment_tx_id']) == 64
    assert result['canonical_validation'] == 'PASS'
    assert result['payment_applied'] is True
    assert result['payment_verified'] is True
    assert (result['agent_a_balance_before'], result['agent_b_balance_before']) == (100, 0)
    assert (result['agent_a_balance_after'], result['agent_b_balance_after']) == (72, 28)
    assert result['service_executed'] is True
    assert result['service_result_verified'] is True
    assert result['receipt_created'] is True
    assert result['receipt_verified'] is True
    assert result['invalid_payment_rejected'] is True
    assert result['replay_rejected'] is True
    assert result['wrong_amount_rejected'] is True
    assert result['wrong_party_rejected'] is True
    assert result['quote_mismatch_rejected'] is True
    assert result['unpaid_work_blocked'] is True
    assert result['tampered_result_rejected'] is True
    assert result['tampered_receipt_rejected'] is True
    assert result['canonical_history_touched'] is False
    assert result['public_network_used'] is False
    assert result['production_keys_used'] is False


def test_structured_text_analysis_is_deterministic_and_useful():
    out = demo.structured_text_analysis('Alpha beta beta. Gamma!')
    assert out['character_count'] == len('Alpha beta beta. Gamma!')
    assert out['word_count'] == 4
    assert out['unique_word_count'] == 3
    assert out['sentence_count'] == 2
    assert out['top_terms'][0] == {'term': 'beta', 'count': 2}
    assert len(out['input_digest']) == 64
    assert out == demo.structured_text_analysis('Alpha beta beta. Gamma!')


def test_request_quote_and_payment_authorization_bind_and_verify(tmp_path):
    payer, provider, _wrong, ledger, request, quote, tx, auth = _base_artifacts(tmp_path)
    assert demo.verify_service_request(request)['service_id'] == demo.SERVICE_ID
    assert demo.verify_service_quote(quote, request=request)['amount'] == 28
    assert demo.verify_payment_intent_binding(request=request, quote=quote, payment_tx=tx, payment_authorization=auth) is True
    ok, tx_id, reason = demo.classify_transfer(ledger, tx)
    assert ok is True and reason == 'ok' and tx_id == tx['id']
    assert asyncio.run(demo.apply_transfer(ledger, tx)) is True
    assert demo.verify_accepted_payment(ledger, request=request, quote=quote, payment_tx=tx, payment_authorization=auth) is True


def test_wrong_amount_party_and_quote_binding_reject_before_application(tmp_path):
    payer, provider, wrong, ledger, request, quote, _tx, _auth = _base_artifacts(tmp_path)
    provider_id = public_identity(_public_key_hex(provider))
    wrong_id = public_identity(_public_key_hex(wrong))

    wrong_amount = build_signed_transfer(payer, receiver=provider_id, amount=27, timestamp=demo.DEMO_TIMESTAMP, nonce=81)
    wrong_amount_auth = demo.build_payment_authorization(payer, request=request, quote=quote, payment_tx=wrong_amount)
    with pytest.raises(demo.DemoError, match='payment_binding_invalid'):
        demo.verify_payment_intent_binding(request=request, quote=quote, payment_tx=wrong_amount, payment_authorization=wrong_amount_auth)

    wrong_party = build_signed_transfer(payer, receiver=wrong_id, amount=28, timestamp=demo.DEMO_TIMESTAMP, nonce=82)
    wrong_party_auth = demo.build_payment_authorization(payer, request=request, quote=quote, payment_tx=wrong_party)
    with pytest.raises(demo.DemoError, match='payment_binding_invalid'):
        demo.verify_payment_intent_binding(request=request, quote=quote, payment_tx=wrong_party, payment_authorization=wrong_party_auth)

    assert (ledger.get_balance(request['payer_identity']), ledger.get_balance(provider_id)) == (100, 0)
    assert ledger.total_transactions == 0


def test_service_cannot_execute_before_payment_verification(monkeypatch):
    called = {'count': 0}
    original = demo.structured_text_analysis

    def wrapped(text):
        called['count'] += 1
        return original(text)

    monkeypatch.setattr(demo, 'structured_text_analysis', wrapped)
    with pytest.raises(demo.DemoError, match='payment_not_verified'):
        demo._perform_paid_service('blocked', payment_verified=False)
    assert called['count'] == 0


def test_result_and_receipt_tampering_fail_closed(tmp_path):
    payer, provider, _wrong, ledger, request, quote, tx, auth = _base_artifacts(tmp_path)
    assert asyncio.run(demo.apply_transfer(ledger, tx)) is True
    assert demo.verify_accepted_payment(ledger, request=request, quote=quote, payment_tx=tx, payment_authorization=auth)
    output = demo._perform_paid_service(request['input']['text'], payment_verified=True)
    result = demo.build_service_result(provider, request=request, quote=quote, payment_tx_id=tx['id'], output=output)
    receipt = demo.build_service_receipt(provider, request=request, quote=quote, service_result=result, payment_tx_id=tx['id'])
    demo.verify_service_result(result, request=request, quote=quote, payment_tx_id=tx['id'])
    demo.verify_service_receipt(receipt, request=request, quote=quote, service_result=result, payment_tx_id=tx['id'])

    bad_result = copy.deepcopy(result)
    bad_result['output']['word_count'] += 1
    with pytest.raises(demo.DemoError):
        demo.verify_service_result(bad_result, request=request, quote=quote, payment_tx_id=tx['id'])

    bad_receipt = copy.deepcopy(receipt)
    bad_receipt['signature'] = '00' * 64
    with pytest.raises(demo.DemoError):
        demo.verify_service_receipt(bad_receipt, request=request, quote=quote, service_result=result, payment_tx_id=tx['id'])


def test_actual_canonical_validation_and_ledger_paths_are_invoked(monkeypatch):
    counts = {'classify': 0, 'apply': 0}
    original_classify = demo.classify_transfer
    original_apply = demo.apply_transfer

    def wrapped_classify(*args, **kwargs):
        counts['classify'] += 1
        return original_classify(*args, **kwargs)

    async def wrapped_apply(*args, **kwargs):
        counts['apply'] += 1
        return await original_apply(*args, **kwargs)

    monkeypatch.setattr(demo, 'classify_transfer', wrapped_classify)
    monkeypatch.setattr(demo, 'apply_transfer', wrapped_apply)
    result = demo.execute_two_agent_service_transaction('verify real paths')
    assert result['canonical_validation'] == 'PASS'
    assert result['payment_applied'] is True
    assert counts['classify'] >= 3
    assert counts['apply'] >= 3


def test_cli_emits_one_public_json_document(capsys):
    code = demo.main(['--input', 'one two two.'])
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload['payment_verified'] is True
    assert payload['service_output']['word_count'] == 3
    combined = captured.out + captured.err
    for forbidden in ('private_key', 'secret_key', 'seed_phrase', 'BEGIN PRIVATE'):
        assert forbidden not in combined


def test_module_has_no_private_serialization_network_rpc_or_subprocess():
    path = Path(demo.__file__)
    src = path.read_text(encoding='utf-8')
    tree = ast.parse(src)
    forbidden_import_roots = {'socket', 'requests', 'urllib', 'http', 'subprocess', 'keyring'}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split('.')[0])
    assert not (imported & forbidden_import_roots)
    assert 'private_bytes' not in src
    assert 'from_private_bytes' not in src
    assert 'os.environ' not in src
    assert 'getenv(' not in src


def test_input_bounds_fail_closed():
    for bad in ('', None, 3, 'x' * (demo.MAX_INPUT_CHARS + 1)):
        with pytest.raises(demo.DemoError):
            demo.execute_two_agent_service_transaction(bad)
