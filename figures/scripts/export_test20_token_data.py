from __future__ import annotations

import argparse
import json
from pathlib import Path

from skillopt_verusage.report_tokens import export_test20_token_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = export_test20_token_data(args.matrix.resolve(), args.output.resolve())
    print(json.dumps({"output": str(args.output), "row_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
