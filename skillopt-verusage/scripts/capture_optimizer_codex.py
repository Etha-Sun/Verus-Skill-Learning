#!/usr/bin/env python3
"""Forward a Codex invocation and retain its JSON events in external storage."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    run_root = Path(os.environ["VERUS_SKILL_RUN_ROOT"]).resolve()
    log_root = Path(os.environ["SKILLOPT_CODEX_TRACE_DIR"]).resolve()
    if run_root not in log_root.parents:
        raise ValueError("optimizer event logs must be below external run storage")
    log_root.mkdir(parents=True, exist_ok=True)
    stem = log_root / uuid.uuid4().hex
    command = [os.environ["SKILLOPT_REAL_CODEX_BIN"], *sys.argv[1:]]
    prompt_path = stem.with_suffix(".prompt.txt")
    prompt_path.write_bytes(sys.stdin.buffer.read())
    prompt_path.chmod(0o600)
    with stem.with_suffix(".stderr").open("wb") as err, prompt_path.open("rb") as prompt:
        proc = subprocess.Popen(command, stdin=prompt, stdout=subprocess.PIPE, stderr=err)
        with stem.with_suffix(".jsonl").open("wb") as out:
            for line in proc.stdout:
                out.write(line)
                out.flush()
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
        status = proc.wait()
    stem.with_suffix(".meta.json").write_text(json.dumps({"command": command, "returncode": status}) + "\n")
    sys.exit(status)


if __name__ == "__main__":
    main()
