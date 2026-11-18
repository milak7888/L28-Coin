# SPDX-License-Identifier: Apache-2.0
"""Offline vector validator A. Validate each branch as an ordered sequence."""

import hashlib
import json

from coin import offline_consensus_vectors as vectors

TEXT_FIELDS = ("profile", "network", "policy", "checkpoint", "parent",
               "transactions", "state")
NUMBER_FIELDS = ("height", "timestamp", "target", "nonce")


def verify_header(header, history, checkpoint):
    if (
        type(header) is not dict
        or set(header) != set(TEXT_FIELDS + NUMBER_FIELDS)
        or any(type(header[name]) is not str for name in TEXT_FIELDS)
        or any(type(header[name]) is not int for name in NUMBER_FIELDS)
        or not 0 <= header["nonce"] < 2**64
    ):
        raise vectors.Rejected("malformed_header")
    for name in ("profile", "network", "policy"):
        if header[name] != checkpoint[name]:
            raise vectors.Rejected("wrong_context")
    if header["checkpoint"] != checkpoint["id"]:
        raise vectors.Rejected("wrong_context")

    height = len(history) + 1
    if header["height"] != height:
        raise vectors.Rejected("wrong_height")
    parent, parent_hash = history[-1] if history else (checkpoint, checkpoint["id"])
    if header["parent"] != parent_hash:
        raise vectors.Rejected("wrong_parent")
    if not parent["timestamp"] < header["timestamp"] < 2**64:
        raise vectors.Rejected("invalid_timestamp")

    required = parent["target"]
    if height >= 3 and (height - 1) % vectors.WINDOW == 0:
        expected = (vectors.WINDOW - 1) * vectors.INTERVAL
        older, _ = history[-vectors.WINDOW]
        observed = parent["timestamp"] - older["timestamp"]
        span = max(expected // 4, min(4 * expected, observed))
        required = max(vectors.MIN_TARGET, min(vectors.MAX_TARGET, required * span // expected))
    if header["target"] != required:
        raise vectors.Rejected("wrong_target")

    payload = json.dumps(header, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    if int.from_bytes(digest, byteorder="big") > required:
        raise vectors.Rejected("insufficient_work")
    return digest.hex()


def select(branches):
    scores = {
        name: sum((1 << 256) // (header["target"] + 1) for header, _ in history)
        for name, history in branches.items()
    }
    maximum = max(scores.values(), default=0)
    leaders = {history[-1][1] for name, history in branches.items()
               if history and scores[name] == maximum}
    if not leaders:
        return "no_valid_tip", None, scores
    if len(leaders) > 1:
        return "pending_equal_work", None, scores
    return "selected", leaders.pop(), scores


if __name__ == "__main__":
    raise SystemExit(vectors.worker_main(verify_header, select))
