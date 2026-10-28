"""Export illustrative final experiment evidence, without model calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vgpu_eval.examples import main

if __name__ == "__main__":
    raise SystemExit(main())
