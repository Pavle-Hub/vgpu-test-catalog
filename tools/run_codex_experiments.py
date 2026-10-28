"""Run isolated Codex pilots or a frozen paired experiment batch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vgpu_eval.codex_batch import main

if __name__ == "__main__":
    raise SystemExit(main())
