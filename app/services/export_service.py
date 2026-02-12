import io
from datetime import datetime, timezone

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAG_FILLS = {
    "green": PatternFill(start_color="27AE60", end_color="27AE60", fill_type="solid"),
    "amber": PatternFill(start_color="F39C12", end_color="F39C12", fill_type="solid"),
    "red": PatternFill(start_color="E74C3C", end_color="E74C3C", fill_type="solid"),
}
WHITE_FONT = Font(color="FFFFFF", bold=True)
HEADER_FILL = PatternFill(start_color="354A5F", end_color="354A5F", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def export_program_health_xlsx(health_data: dict) -> io.BytesIO:
    """
    Generate a styled Excel workbook from program health data.
    Returns a BytesIO buffer ready for Flask send_file.
    """
    wb = Workbook()

    # ── Sheet 1: Executive Summary ────────────────────────────────────
    ws = wb.active
    ws.title = "Executive Summary"

    # Title row
    ws.merge_cells("A1:F1")
    ws["A1"] = f"Program Health Report — {health_data['program_name']}"
    ws["A1"].font = Font(size=16, bold=True)
    ws["A2"] = f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    ws["A2"].font = Font(size=10, italic=True, color="666666")

    if health_data.get("days_to_go_live") is not None:
        ws["D2"] = f"Days to Go-Live: {health_data['days_to_go_live']}"
        ws["D2"].font = Font(size=11, bold=True)

    # Overall RAG
    ws["A4"] = "Overall Status"
    ws["A4"].font = Font(size=12, bold=True)
    ws["B4"] = health_data["overall_rag"].upper()
    ws["B4"].fill = RAG_FILLS.get(health_data["overall_rag"], RAG_FILLS["amber"])
    ws["B4"].font = WHITE_FONT
    ws["B4"].alignment = Alignment(horizontal="center")

    # Area breakdown table
    row = 6
    headers = ["Area", "RAG", "Key Metric", "Value", "Details"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = THIN_BORDER

    areas = health_data.get("areas", {})
    area_rows = [
        (
            "Explore",
            areas.get("explore", {}),
            "Workshop Completion",
            f"{areas.get('explore', {}).get('workshops', {}).get('pct', 0)}%",
            f"{areas.get('explore', {}).get('requirements', {}).get('total', 0)} reqs, "
            f"{areas.get('explore', {}).get('open_items', {}).get('overdue', 0)} overdue OIs",
        ),
        (
            "Backlog",
            areas.get("backlog", {}),
            "Completion",
            f"{areas.get('backlog', {}).get('items', {}).get('pct', 0)}%",
            f"{areas.get('backlog', {}).get('items', {}).get('total', 0)} total items",
        ),
        (
            "Testing",
            areas.get("testing", {}),
            "Pass Rate",
            f"{areas.get('testing', {}).get('pass_rate', 0)}%",
            f"{areas.get('testing', {}).get('defects', {}).get('open', 0)} open defects, "
            f"{areas.get('testing', {}).get('defects', {}).get('s1_open', 0)} S1",
        ),
        (
            "RAID",
            areas.get("raid", {}),
            "Open Risks",
            f"{areas.get('raid', {}).get('risks_open', 0)}",
            f"{areas.get('raid', {}).get('risks_red', 0)} red risks, "
            f"{areas.get('raid', {}).get('actions_overdue', 0)} overdue actions",
        ),
        (
            "Integration",
            areas.get("integration", {}),
            "Live %",
            f"{areas.get('integration', {}).get('interfaces', {}).get('pct', 0)}%",
            f"{areas.get('integration', {}).get('interfaces', {}).get('total', 0)} total interfaces",
        ),
    ]

    for area_name, area_data, metric, value, details in area_rows:
        row += 1
        ws.cell(row=row, column=1, value=area_name).border = THIN_BORDER
        rag_cell = ws.cell(row=row, column=2, value=area_data.get("rag", "—").upper())
        rag_cell.fill = RAG_FILLS.get(area_data.get("rag", ""), PatternFill())
        rag_cell.font = WHITE_FONT
        rag_cell.alignment = Alignment(horizontal="center")
        rag_cell.border = THIN_BORDER
        ws.cell(row=row, column=3, value=metric).border = THIN_BORDER
        ws.cell(row=row, column=4, value=value).border = THIN_BORDER
        ws.cell(row=row, column=5, value=details).border = THIN_BORDER

    for col in range(1, 6):
        ws.column_dimensions[get_column_letter(col)].width = [20, 10, 22, 12, 45][col - 1]

    # ── Sheet 2: Phase Timeline ───────────────────────────────────────
    ws2 = wb.create_sheet("Phases")
    headers2 = ["Phase", "Status", "Completion %", "Planned Start", "Planned End"]
    for col, header in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = THIN_BORDER

    for i, phase in enumerate(health_data.get("phases", []), 2):
        ws2.cell(row=i, column=1, value=phase["name"]).border = THIN_BORDER
        ws2.cell(row=i, column=2, value=phase["status"]).border = THIN_BORDER
        pct_cell = ws2.cell(row=i, column=3, value=phase["completion_pct"])
        pct_cell.border = THIN_BORDER
        pct_cell.alignment = Alignment(horizontal="center")
        ws2.cell(row=i, column=4, value=phase.get("planned_start", "")).border = THIN_BORDER
        ws2.cell(row=i, column=5, value=phase.get("planned_end", "")).border = THIN_BORDER

    for col in range(1, 6):
        ws2.column_dimensions[get_column_letter(col)].width = [25, 12, 14, 14, 14][col - 1]

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def export_program_health_html(health_data: dict) -> str:
    """
    Generate an HTML report suitable for printing / PDF conversion.
    Returns HTML string with inline CSS for print-friendliness.
    """
    rag_colors = {"green": "#27AE60", "amber": "#F39C12", "red": "#E74C3C"}
    areas = health_data.get("areas", {})

    area_rows_html = ""
    for name, key in [
        ("Explore", "explore"),
        ("Backlog", "backlog"),
        ("Testing", "testing"),
        ("RAID", "raid"),
        ("Integration", "integration"),
    ]:
        area = areas.get(key, {})
        rag = area.get("rag", "—")
        color = rag_colors.get(rag, "#999")
        area_rows_html += f"""
        <tr>
            <td style=\"font-weight:600\">{name}</td>
            <td style=\"background:{color};color:#fff;text-align:center;font-weight:700;border-radius:4px\">{rag.upper()}</td>
        </tr>"""

    phases_html = ""
    for phase in health_data.get("phases", []):
        phases_html += f"""
        <tr>
            <td>{phase['name']}</td>
            <td>{phase['status']}</td>
            <td style=\"text-align:center\">{phase['completion_pct']}%</td>
            <td>{phase.get('planned_start', '')}</td>
            <td>{phase.get('planned_end', '')}</td>
        </tr>"""

    overall_rag = health_data.get("overall_rag", "—")
    overall_color = rag_colors.get(overall_rag, "#999")

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset=\"utf-8\">
<title>Program Health Report — {health_data['program_name']}</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
    h1 {{ color: #354A5F; margin-bottom: 4px; }}
    .meta {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
    .overall {{ display: inline-block; padding: 8px 24px; background: {overall_color};
                color: #fff; font-weight: 700; font-size: 18px; border-radius: 6px; margin: 12px 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th {{ background: #354A5F; color: #fff; padding: 10px 12px; text-align: left; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #e0e0e0; }}
    tr:hover {{ background: #f5f7fa; }}
    @media print {{ body {{ margin: 20px; }} }}
</style>
</head><body>
<h1>Program Health Report</h1>
<p class=\"meta\">{health_data['program_name']} — Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
{f" — Go-Live in {health_data['days_to_go_live']} days" if health_data.get('days_to_go_live') else ""}</p>

<div class=\"overall\">{overall_rag.upper()}</div>

<h2>Area Health</h2>
<table><thead><tr><th>Area</th><th style=\"width:100px\">RAG</th></tr></thead>
<tbody>{area_rows_html}</tbody></table>

<h2>Phase Timeline</h2>
<table><thead><tr><th>Phase</th><th>Status</th><th>Completion</th><th>Start</th><th>End</th></tr></thead>
<tbody>{phases_html}</tbody></table>

</body></html>"""

    return html
