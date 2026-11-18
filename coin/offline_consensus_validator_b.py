# SPDX-License-Identifier: Apache-2.0
"""Offline vector validator B. Validate parent transitions and rank valid tips."""

from collections import defaultdict
from hashlib import sha256
from json import JSONEncoder

from coin import offline_consensus_vectors as vectors

FIELD_TYPES = {
    "profile": str, "network": str, "policy": str, "checkpoint": str,
    "parent": str, "height": int, "timestamp": int, "transactions": str,
    "state": str, "target": int, "nonce": int,
}


def verify_header(header, history, checkpoint):
    if type(header) is not dict or header.keys() != FIELD_TYPES.keys():
        raise vectors.Rejected("malformed_header")
    for field, required_type in FIELD_TYPES.items():
        if type(header[field]) is not required_type:
            raise vectors.Rejected("malformed_header")
    if header["nonce"] < 0 or header["nonce"].bit_length() > 64:
        raise vectors.Rejected("malformed_header")
    actual_context = (header["profile"], header["network"],
                      header["policy"], header["checkpoint"])
    trusted_context = (checkpoint["profile"], checkpoint["network"],
                       checkpoint["policy"], checkpoint["id"])
    if actual_context != trusted_context:
        raise vectors.Rejected("wrong_context")

    ancestry = [(checkpoint, checkpoint["id"]), *history]
    previous, previous_id = ancestry[-1]
    new_height = previous["height"] + 1
    if new_height != header["height"]:
        raise vectors.Rejected("wrong_height")
    if previous_id != header["parent"]:
        raise vectors.Rejected("wrong_parent")
    if header["timestamp"] <= previous["timestamp"] or header["timestamp"].bit_length() > 64:
        raise vectors.Rejected("invalid_timestamp")

    target = previous["target"]
    if previous["height"] > 0 and previous["height"] % vectors.WINDOW == 0:
        observed = previous["timestamp"] - ancestry[-vectors.WINDOW][0]["timestamp"]
        expected = vectors.INTERVAL * (vectors.WINDOW - 1)
        span = sorted((observed, expected // 4, expected * 4))[1]
        adjusted, _ = divmod(span * target, expected)
        target = sorted((adjusted, vectors.MIN_TARGET, vectors.MAX_TARGET))[1]
    if target != header["target"]:
        raise vectors.Rejected("wrong_target")

    encoder = JSONEncoder(ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(",", ":"))
    text = "".join(encoder.iterencode(header))
    digest = sha256(bytes(text, encoding="utf-8")).hexdigest()
    if int(digest, 16) > target:
        raise vectors.Rejected("insufficient_work")
    return digest


def select(branches):
    by_score = defaultdict(set)
    branch_scores = {}
    for name, chain in branches.items():
        total = 0
        for header, _ in chain:
            quotient, _ = divmod(2**256, header["target"] + 1)
            total += quotient
        branch_scores[name] = total
        if chain:
            by_score[total].add(chain[-1][1])

    if not by_score:
        return "no_valid_tip", None, branch_scores
    winning_tips = by_score[sorted(by_score)[-1]]
    if len(winning_tips) == 1:
        return "selected", next(iter(winning_tips)), branch_scores
    return "pending_equal_work", None, branch_scores


if __name__ == "__main__":
    raise SystemExit(vectors.worker_main(verify_header, select))
