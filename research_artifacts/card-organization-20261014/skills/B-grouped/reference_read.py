import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
manifest = json.loads((root / "reference_manifest.json").read_text())
ident = sys.argv[1] if len(sys.argv) == 2 else ""
entry = manifest.get(ident)
if entry is None:
    print(json.dumps({"reference_retrieval": 1, "error": "unknown reference id", "id": ident}))
    raise SystemExit(2)
path = root / entry["path"]
resolved = path.resolve()
if path.is_symlink() or root / "references" not in resolved.parents:
    raise SystemExit("unsafe reference path")
body = path.read_bytes()
if hashlib.sha256(body).hexdigest() != entry["sha256"]:
    raise SystemExit("reference hash mismatch")
print(json.dumps({"reference_retrieval": 1, "operation": "read", "id": ident,
                  "source_card_ids": entry["source_card_ids"], "bytes": len(body),
                  "sha256": entry["sha256"], "content": body.decode()}, ensure_ascii=False))
