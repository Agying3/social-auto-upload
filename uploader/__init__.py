from pathlib import Path

from conf import DATA_DIR

Path(DATA_DIR / "cookies").mkdir(parents=True, exist_ok=True)
