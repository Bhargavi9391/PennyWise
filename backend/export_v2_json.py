import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent / "v2_full_run2"
OUT = BASE / "json"
OUT.mkdir(exist_ok=True)

files = list(BASE.glob("*.csv"))

for path in files:
    output = OUT / f"{path.stem}.json"
    with path.open(encoding="utf-8-sig", newline="") as src:
        with output.open("w", encoding="utf-8") as dst:
            dst.write("[\n")
            writer = None
            first = True
            for row in csv.DictReader(src):
                if not first:
                    dst.write(",\n")
                json.dump(row, dst, ensure_ascii=False)
                first = False
            dst.write("\n]\n")
    print("EXPORTED:", output.name)

print("JSON EXPORT COMPLETE")
