import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
app = importlib.import_module("app.main").app


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(target)


if __name__ == "__main__":
    main()
