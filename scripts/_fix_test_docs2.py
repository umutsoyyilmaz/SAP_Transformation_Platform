"""Fix remaining 2 xfail blocks + MinutesGenerator calls in test_workshop_docs_isolation.py."""
import pathlib

filepath = pathlib.Path("tests/test_workshop_docs_isolation.py")
content = filepath.read_text()

# ── Fix 1: Remove xfail from test_cross_project_generate_is_blocked ──────────
old1 = (
    "    # \u2500\u2500 Isolation (xfail \u2014 documents desired post-fix behavior) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "\n"
    "    @pytest.mark.xfail(\n"
    "        strict=False,\n"
    "        reason=(\n"
    '            "P0 isolation gap: WorkshopDocumentService.generate has no project_id "\n'
    '            "parameter. A caller that knows ws_b_id can generate and persist a "\n'
    '            "document tagged to project_b without any authorization check. "\n'
    '            "Fix: add project_id param + reject when ws.project_id != project_id."\n'
    "        ),\n"
    "    )\n"
    "    def test_cross_project_generate_is_blocked(self, two_projects):\n"
    '        """Project A MUST NOT generate documents for project B\'s workshop.\n'
    "\n"
    "        VULNERABILITY TODAY: generate(ws_b_id) succeeds, writes a document\n"
    "        with project_id=prog_b_id \u2014 a cross-tenant write with no auth check.\n"
    "        EXPECTED AFTER FIX: raise ValueError/PermissionError.\n"
    '        """\n'
    "        with pytest.raises((ValueError, PermissionError)):\n"
    '            WorkshopDocumentService.generate(\n'
    '                two_projects["ws_b_id"], "meeting_minutes"\n'
    "            )\n"
    "\n"
    "    @pytest.mark.xfail(\n"
    "        strict=False,\n"
    '        reason="P0 isolation gap: see test_cross_project_generate_is_blocked.",\n'
    "    )\n"
    "    def test_cross_project_traceability_report_is_blocked(self, two_projects):\n"
    "        \"\"\"Traceability report for project_b's workshop must be rejected by project_a caller.\"\"\"\n"
    "        with pytest.raises((ValueError, PermissionError)):\n"
    '            WorkshopDocumentService.generate(\n'
    '                two_projects["ws_b_id"], "traceability_report"\n'
    "            )"
)

new1 = (
    "    # \u2500\u2500 Isolation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "\n"
    "    def test_cross_project_generate_is_blocked(self, two_projects):\n"
    '        """Project A MUST NOT generate documents for project B\'s workshop.\n'
    "\n"
    "        Verification that P0 isolation gap is closed: project_a's project_id\n"
    "        is passed but ws_b belongs to project_b \u2014 must raise ValueError.\n"
    '        """\n'
    "        with pytest.raises(ValueError):\n"
    '            WorkshopDocumentService.generate(\n'
    '                two_projects["ws_b_id"], "meeting_minutes", project_id=two_projects["prog_a_id"]\n'
    "            )\n"
    "\n"
    "    def test_cross_project_traceability_report_is_blocked(self, two_projects):\n"
    "        \"\"\"Traceability report for project_b's workshop must be rejected by project_a caller.\"\"\"\n"
    "        with pytest.raises(ValueError):\n"
    '            WorkshopDocumentService.generate(\n'
    '                two_projects["ws_b_id"], "traceability_report", project_id=two_projects["prog_a_id"]\n'
    "            )"
)

if old1 in content:
    content = content.replace(old1, new1)
    print("Replaced WorkshopDocumentService xfail blocks")
else:
    print("ERROR: WorkshopDocumentService xfail block NOT FOUND")
    # Debug: show what's around line 208
    for i, line in enumerate(content.splitlines()[205:245], 206):
        print(f"{i}: {repr(line)}")

# ── Fix 2: MinutesGeneratorService.generate() happy-path calls ───────────────
replacements = [
    (
        'MinutesGeneratorService.generate(two_projects["ws_a_id"])\n',
        'MinutesGeneratorService.generate(two_projects["ws_a_id"], project_id=two_projects["prog_a_id"])\n',
    ),
    (
        'MinutesGeneratorService.generate(two_projects["ws_a_id"], session_number=1\n        )',
        'MinutesGeneratorService.generate(\n            two_projects["ws_a_id"], project_id=two_projects["prog_a_id"], session_number=1\n        )',
    ),
    (
        'MinutesGeneratorService.generate(\n                "deadbeef-dead-beef-dead-beefdeadbeef"\n            )',
        'MinutesGeneratorService.generate(\n                "deadbeef-dead-beef-dead-beefdeadbeef", project_id=999\n            )',
    ),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"OK: replaced {repr(old[:60])}")
    else:
        print(f"MISS: {repr(old[:60])}")

# ── Fix 3: MinutesGeneratorService xfail block ───────────────────────────────
old_xfail_minutes = (
    "    # \u2500\u2500 Isolation (xfail) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "\n"
    "    @pytest.mark.xfail(\n"
    "        strict=False,\n"
    "        reason=(\n"
    '            "P0 isolation gap: MinutesGeneratorService.generate has no project_id "\n'
    '            "parameter. Any caller that knows ws_b_id can trigger minutes "\n'
    '            "generation for project_b\'s workshop and read the output. "\n'
    '            "Fix: add project_id parameter + ownership verification."\n'
    "        ),\n"
    "    )\n"
    "    def test_cross_project_minutes_generation_is_blocked(self, two_projects):\n"
    '        """Project A caller MUST NOT generate minutes for project B\'s workshop.\n'
    "\n"
    "        VULNERABILITY TODAY: call succeeds, returns project_b data.\n"
    "        EXPECTED AFTER FIX: raise ValueError/PermissionError.\n"
    '        """\n'
    "        with pytest.raises((ValueError, PermissionError)):\n"
    '            MinutesGeneratorService.generate(two_projects["ws_b_id"])'
)
new_no_xfail_minutes = (
    "    # \u2500\u2500 Isolation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "\n"
    "    def test_cross_project_minutes_generation_is_blocked(self, two_projects):\n"
    '        """Project A caller MUST NOT generate minutes for project B\'s workshop.\n'
    "\n"
    "        Verification that P0 isolation gap is closed: project_a's project_id\n"
    "        is passed but ws_b belongs to project_b \u2014 must raise ValueError.\n"
    '        """\n'
    "        with pytest.raises(ValueError):\n"
    '            MinutesGeneratorService.generate(two_projects["ws_b_id"], project_id=two_projects["prog_a_id"])'
)
if old_xfail_minutes in content:
    content = content.replace(old_xfail_minutes, new_no_xfail_minutes)
    print("Replaced MinutesGenerator xfail block")
else:
    print("MISS: MinutesGenerator xfail block not found")

# ── Fix 4: generate_ai_summary() calls ───────────────────────────────────────
ai_replacements = [
    (
        'MinutesGeneratorService.generate_ai_summary(two_projects["ws_a_id"])\n',
        'MinutesGeneratorService.generate_ai_summary(two_projects["ws_a_id"], project_id=two_projects["prog_a_id"])\n',
    ),
    (
        'MinutesGeneratorService.generate_ai_summary(\n                "00000000-0000-0000-0000-000000000000"\n            )',
        'MinutesGeneratorService.generate_ai_summary(\n                "00000000-0000-0000-0000-000000000000", project_id=999\n            )',
    ),
]
for old, new in ai_replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"OK: AI replace {repr(old[:60])}")
    else:
        print(f"MISS: AI {repr(old[:60])}")

# ── Fix 5: generate_ai_summary xfail block ───────────────────────────────────
old_ai_xfail = (
    "    @pytest.mark.xfail(\n"
    "        strict=False,\n"
    "        reason=(\n"
    '            "P0 isolation gap: generate_ai_summary has no project_id parameter. "\n'
    '            "Any caller can retrieve AI-aggregated data for another project\'s workshop."\n'
    "        ),\n"
    "    )\n"
    "    def test_cross_project_ai_summary_is_blocked(self, two_projects):\n"
    '        """Project A must not receive AI summary data for project B\'s workshop."""\n'
    "        with pytest.raises((ValueError, PermissionError)):\n"
    '            MinutesGeneratorService.generate_ai_summary(two_projects["ws_b_id"])'
)
new_ai_no_xfail = (
    "    def test_cross_project_ai_summary_is_blocked(self, two_projects):\n"
    '        """Project A must not receive AI summary data for project B\'s workshop.\n'
    "\n"
    "        Verification that P0 isolation gap is closed: project_a's project_id\n"
    "        is passed but ws_b belongs to project_b \u2014 must raise ValueError.\n"
    '        """\n'
    "        with pytest.raises(ValueError):\n"
    '            MinutesGeneratorService.generate_ai_summary(two_projects["ws_b_id"], project_id=two_projects["prog_a_id"])'
)
if old_ai_xfail in content:
    content = content.replace(old_ai_xfail, new_ai_no_xfail)
    print("Replaced AI summary xfail block")
else:
    print("MISS: AI summary xfail block not found")

# Write out
filepath.write_text(content)
remaining = content.count("@pytest.mark.xfail(")
print(f"\nFinal xfail decorator count: {remaining} (expect 0)")
