"""One-shot script: fix remaining test_workshop_docs_isolation.py calls."""
import pathlib

filepath = pathlib.Path("tests/test_workshop_docs_isolation.py")
content = filepath.read_text()

# ── MinutesGeneratorService.generate() calls ─────────────────────────────────

# Happy-path calls (ws_a with no project_id → add project_id=...)
content = content.replace(
    'MinutesGeneratorService.generate(two_projects["ws_a_id"])\n',
    'MinutesGeneratorService.generate(two_projects["ws_a_id"], project_id=two_projects["prog_a_id"])\n',
)
content = content.replace(
    'MinutesGeneratorService.generate(two_projects["ws_a_id"], session_number=1\n        )',
    'MinutesGeneratorService.generate(two_projects["ws_a_id"], project_id=two_projects["prog_a_id"], session_number=1\n        )',
)

# Nonexistent workshop test
content = content.replace(
    'MinutesGeneratorService.generate(\n                "deadbeef-dead-beef-dead-beefdeadbeef"\n            )',
    'MinutesGeneratorService.generate(\n                "deadbeef-dead-beef-dead-beefdeadbeef", project_id=999\n            )',
)

# xfail block: test_cross_project_minutes_generation_is_blocked
old_minutes_xfail = (
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
new_minutes_no_xfail = (
    "    def test_cross_project_minutes_generation_is_blocked(self, two_projects):\n"
    '        """Project A caller MUST NOT generate minutes for project B\'s workshop.\n'
    "\n"
    "        Verification that P0 isolation gap is closed: project_a's project_id is\n"
    "        passed but ws_b belongs to project_b — must raise ValueError.\n"
    '        """\n'
    "        with pytest.raises(ValueError):\n"
    '            MinutesGeneratorService.generate(two_projects["ws_b_id"], project_id=two_projects["prog_a_id"])'
)
content = content.replace(old_minutes_xfail, new_minutes_no_xfail)

# ── MinutesGeneratorService.generate_ai_summary() calls ──────────────────────

# Happy-path calls
content = content.replace(
    'MinutesGeneratorService.generate_ai_summary(two_projects["ws_a_id"])\n',
    'MinutesGeneratorService.generate_ai_summary(two_projects["ws_a_id"], project_id=two_projects["prog_a_id"])\n',
)

# Nonexistent workshop test
content = content.replace(
    'MinutesGeneratorService.generate_ai_summary(\n                "00000000-0000-0000-0000-000000000000"\n            )',
    'MinutesGeneratorService.generate_ai_summary(\n                "00000000-0000-0000-0000-000000000000", project_id=999\n            )',
)

# xfail block: test_cross_project_ai_summary_is_blocked
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
    "        Verification that P0 isolation gap is closed: project_a's project_id is\n"
    "        passed but ws_b belongs to project_b — must raise ValueError.\n"
    '        """\n'
    "        with pytest.raises(ValueError):\n"
    '            MinutesGeneratorService.generate_ai_summary(two_projects["ws_b_id"], project_id=two_projects["prog_a_id"])'
)
content = content.replace(old_ai_xfail, new_ai_no_xfail)

# ── WorkshopDocumentService xfail blocks (2 remaining) ───────────────────────
old_nonexistent = (
    '"00000000-0000-0000-0000-000000000000", "meeting_minutes"\n'
    "            )\n"
)
new_nonexistent = (
    '"00000000-0000-0000-0000-000000000000", "meeting_minutes", project_id=999\n'
    "            )\n"
)
content = content.replace(old_nonexistent, new_nonexistent, 1)  # only first occurrence

old_isolation_header = (
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
new_isolation_body = (
    "    # \u2500\u2500 Isolation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "\n"
    "    def test_cross_project_generate_is_blocked(self, two_projects):\n"
    '        """Project A MUST NOT generate documents for project B\'s workshop.\n'
    "\n"
    "        Verification that P0 isolation gap is closed: project_a's project_id is\n"
    "        passed but ws_b belongs to project_b \u2014 must raise ValueError.\n"
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
content = content.replace(old_isolation_header, new_isolation_body)

filepath.write_text(content)

remaining_xfails = content.count("@pytest.mark.xfail")
print(f"Done. Remaining xfail count: {remaining_xfails}")
