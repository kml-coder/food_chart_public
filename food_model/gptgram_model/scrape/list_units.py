import json
from collections import Counter
from pathlib import Path


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    file_path = base_dir / "output.json"
    units_txt_path = base_dir / "unit_list.txt"
    counts_csv_path = base_dir / "unit_counts.csv"

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    units = [item.get("unit", "").strip() for item in data if isinstance(item, dict)]
    units = [u for u in units if u]

    counter = Counter(units)

    print(f"Total rows: {len(data)}")
    print(f"Unique non-empty units: {len(counter)}\n")

    # Save alphabetical unit list
    sorted_units = sorted(counter)
    with units_txt_path.open("w", encoding="utf-8") as f:
        for unit in sorted_units:
            f.write(f"{unit}\n")

    # Save counts by frequency in CSV
    with counts_csv_path.open("w", encoding="utf-8") as f:
        f.write("unit,count\n")
        for unit, count in counter.most_common():
            safe_unit = unit.replace('"', '""')
            f.write(f"\"{safe_unit}\",{count}\n")

    print(f"Saved unit list: {units_txt_path.name}")
    print(f"Saved unit counts: {counts_csv_path.name}\n")

    print("=== Units (alphabetical) ===")
    for unit in sorted_units:
        print(unit)

    print("\n=== Counts by unit (desc) ===")
    for unit, count in counter.most_common():
        print(f"{unit}: {count}")


if __name__ == "__main__":
    main()
