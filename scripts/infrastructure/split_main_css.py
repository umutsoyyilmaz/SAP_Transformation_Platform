#!/usr/bin/env python3
"""
D2 — Split main.css into 6 domain CSS files.

Run from project root:
    python3 scripts/infrastructure/split_main_css.py
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CSS_DIR = os.path.join(ROOT, "static", "css")
SOURCE = os.path.join(CSS_DIR, "main.css")

# (filename, start_line_1indexed, end_line_1indexed_inclusive)
# None for end = read to end of file
SPLITS = [
    (
        "base.css",
        1,
        798,
        "Base styles: variables, reset, typography, shell, sidebar, layout, "
        "buttons, modal, form, toast, empty-state, loading.",
    ),
    (
        "program-views.css",
        799,
        1215,
        "Program/project view styles: tabs, phase card, completion bar, "
        "badge variants, scenario/workshop cards, filter bar, traceability.",
    ),
    (
        "project-setup.css",
        1216,
        1393,
        "Project setup wizard and configuration view styles.",
    ),
    (
        "backlog.css",
        1394,
        1663,
        "Backlog views: kanban board, kanban card, WRICEF badge, sprint card, "
        "detail tabs (FS/TS/Tests/Trace), traceability badge.",
    ),
    (
        "raid-ai.css",
        1664,
        2546,
        "RAID & Notification (Sprint 6), AI Query view (Sprint 8), "
        "suggestion badge dropdown, calendar.",
    ),
    (
        "explore.css",
        2547,
        None,
        "Explore phase: workshop, process hierarchy, gap analysis, "
        "fit-to-standard views and all associated components.",
    ),
]


def split():
    with open(SOURCE, encoding="utf-8") as fh:
        all_lines = fh.readlines()

    total = len(all_lines)
    print(f"Source: {SOURCE}  ({total} lines)")
    print()

    for filename, start, end, description in SPLITS:
        chunk = all_lines[start - 1 : end]
        dest = os.path.join(CSS_DIR, filename)
        header = (
            f"/*\n"
            f" * {filename}\n"
            f" * D2 refactor — split from main.css\n"
            f" *\n"
            f" * {description}\n"
            f" *\n"
            f" * Source lines: {start}–{end if end else total}\n"
            f" */\n\n"
        )
        with open(dest, "w", encoding="utf-8") as out:
            out.write(header)
            out.writelines(chunk)
        print(f"  ✓ {filename:25s}  {len(chunk):4d} lines  →  {dest}")

    print()
    print("Done. Next steps:")
    print("  1. Update templates/index.html: replace main.css <link> with 6 new files.")
    print("  2. Replace static/css/main.css content with @import shim.")
    print("  3. Browser-test every major view.")


if __name__ == "__main__":
    split()
