"""Write CATALOG.md: every piece with its version, the kinds of app it fits and what it shows."""
import json
from pathlib import Path

LIBRARY = Path(__file__).resolve().parent.parent


def rows(platform: str) -> list[str]:
    lines = []
    for entry_file in sorted((LIBRARY / "entries" / platform).glob("*/*/entry.json")):
        entry = json.loads(entry_file.read_text())
        name = f"{entry_file.parent.parent.name}/{entry_file.parent.name}"
        kinds = ", ".join(entry.get("kinds", []))
        lines.append(f"| {name} | {entry.get('version', '')} | {kinds} | {entry.get('line', '')} |")
    return lines


def main() -> None:
    parts = ["# Catalog", "", "Written by `python3 tools/catalog.py`. Do not edit by hand.", ""]
    for platform in ("mobile", "web"):
        found = rows(platform)
        if found:
            parts += [f"## {platform} ({len(found)} pieces)", "", "| piece | version | fits | what it shows |",
                      "|---|---|---|---|", *found, ""]
    (LIBRARY / "CATALOG.md").write_text("\n".join(parts))


if __name__ == "__main__":
    main()
