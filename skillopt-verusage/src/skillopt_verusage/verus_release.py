"""Pinned formal Verus release identity for comparable evaluation."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


FORMAL_VERUS_TAG = "release/0.2025.09.12.bb1f342"
FORMAL_VERUS_VERSION = "0.2025.09.12.bb1f342"
FORMAL_VERUS_COMMIT = "bb1f342683fd26de011825725a55325b65e7d359"


def read_verus_identity(verus_bin: Path) -> dict[str, Any]:
    resolved = verus_bin.resolve()
    if not resolved.is_file():
        raise ValueError(f"Verus binary does not exist: {resolved}")
    completed = subprocess.run(
        [str(resolved), "--version", "--output-json"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(
            f"Verus version probe failed ({completed.returncode}): "
            f"{completed.stderr[-1000:]}"
        )
    try:
        payload = json.loads(completed.stdout)
        identity = payload["verus"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("Verus version probe returned invalid JSON") from error
    if not isinstance(identity, dict):
        raise ValueError("Verus identity must be a JSON object")
    return identity


def validate_formal_verus(identity: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "version": FORMAL_VERUS_VERSION,
        "commit": FORMAL_VERUS_COMMIT,
        "profile": "release",
    }
    mismatches = {
        key: {"expected": value, "actual": identity.get(key)}
        for key, value in expected.items()
        if identity.get(key) != value
    }
    if mismatches:
        raise ValueError(f"formal Verus identity mismatch: {mismatches}")
    return {
        "tag": FORMAL_VERUS_TAG,
        "version": identity["version"],
        "commit": identity["commit"],
        "profile": identity["profile"],
        "platform": identity.get("platform"),
        "toolchain": identity.get("toolchain"),
    }


def require_formal_verus(verus_bin: Path) -> dict[str, Any]:
    return validate_formal_verus(read_verus_identity(verus_bin))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verus-bin", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(require_formal_verus(args.verus_bin), indent=2))


if __name__ == "__main__":
    main()
