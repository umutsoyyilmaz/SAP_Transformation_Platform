"""Fix test_workshop_docs_isolation.py using line-range replacement (avoids Unicode matching issues)."""
import pathlib

filepath = pathlib.Path("tests/test_workshop_docs_isolation.py")
lines = filepath.read_text().splitlines(keepends=True)

# Print lines around the xfail to confirm indices (0-based)
print("=== Lines 207-242 (0-based) ===")
for i in range(207, min(243, len(lines))):
    print(f"  [{i}] {repr(lines[i][:90])}")

# Lines 207-241 (0-based) = lines 208-242 (1-based)
# Replace with the fixed content
new_block = """\
    # \u2500\u2500 Isolation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def test_cross_project_generate_is_blocked(self, two_projects):
        \"\"\"Project A MUST NOT generate documents for project B's workshop.

        Verification that P0 isolation gap is closed: project_a's project_id
        is passed but ws_b belongs to project_b \u2014 must raise ValueError.
        \"\"\"
        with pytest.raises(ValueError):
            WorkshopDocumentService.generate(
                two_projects["ws_b_id"], "meeting_minutes", project_id=two_projects["prog_a_id"]
            )

    def test_cross_project_traceability_report_is_blocked(self, two_projects):
        \"\"\"Traceability report for project_b's workshop must be rejected by project_a caller.\"\"\"
        with pytest.raises(ValueError):
            WorkshopDocumentService.generate(
                two_projects["ws_b_id"], "traceability_report", project_id=two_projects["prog_a_id"]
            )

"""

# Find the exact start/end lines
# Start: line with "# ── Isolation (xfail" (0-based index)
# End: the blank line after the last test (241, 0-based)
start_idx = None
for i, line in enumerate(lines):
    if "# \u2500\u2500 Isolation (xfail" in line and i > 200:
        start_idx = i
        break

if start_idx is None:
    print("ERROR: Could not find start line")
    exit(1)

# Find end: after the second xfail test (find "traceability_report" test's closing ")")
end_idx = start_idx
for i in range(start_idx, min(start_idx + 50, len(lines))):
    if '"traceability_report"' in lines[i]:
        # Find the closing ) after this
        for j in range(i, min(i + 5, len(lines))):
            if lines[j].strip() == ")":
                end_idx = j + 1  # include the blank line after
                break
        break

print(f"\nWill replace lines {start_idx}-{end_idx} (0-based)")
print(f"  Start: {repr(lines[start_idx][:80])}")
print(f"  End:   {repr(lines[end_idx-1][:80])}")

# Build new content
new_lines = lines[:start_idx] + [new_block] + lines[end_idx:]
filepath.write_text("".join(new_lines))

# Verify
remaining = "".join(new_lines).count("@pytest.mark.xfail(")
print(f"\nFinal xfail count: {remaining} (expect 0 for workshop docs class)")
print("Done.")
