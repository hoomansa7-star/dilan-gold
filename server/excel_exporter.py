# -*- coding: utf-8 -*-
"""
Excel export engine for Dilan Gold ERP.
Complies strictly with user_global rules:
- ws.sheet_view.rightToLeft = True
- Visible gridlines
- High precision gold decimal formatting (3 decimals for grams)
- Professional Persian styling with gold/charcoal accents
"""

import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import Dict, Any, List


def apply_table_styles(ws, max_row: int, max_col: int):
    """Enforces visible gridlines, right-to-left layout, and column widths."""
    ws.sheet_view.rightToLeft = True
    if ws.views.sheetView:
        ws.views.sheetView[0].showGridLines = True

    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )

    for row in range(1, max_row + 1):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            if not cell.border.left.style:
                cell.border = thin_border

    # Auto-adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 5, 14)


def export_shift_to_excel(shift_data: Dict[str, Any], tasks: List[Dict[str, Any]], batches: List[Dict[str, Any]], incidents: List[Dict[str, Any]]) -> io.BytesIO:
    """Exports a daily workshop shift into a beautifully styled Persian Excel sheet."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"کارگاه {shift_data.get('date_shamsi', 'روزانه')}".replace('/', '-')

    # Fonts & Fills
    title_font = Font(name="Tahoma", size=15, bold=True, color="FFFFFF")
    header_font = Font(name="Tahoma", size=11, bold=True, color="FFFFFF")
    sub_header_font = Font(name="Tahoma", size=11, bold=True, color="222222")
    data_font = Font(name="Tahoma", size=10, color="111111")
    bold_font = Font(name="Tahoma", size=10, bold=True, color="111111")
    loss_font = Font(name="Tahoma", size=10, bold=True, color="B91C1C")

    gold_dark_fill = PatternFill(start_color="1F2430", end_color="1F2430", fill_type="solid")
    gold_header_fill = PatternFill(start_color="997B2A", end_color="997B2A", fill_type="solid")
    accent_fill = PatternFill(start_color="F7F4EB", end_color="F7F4EB", fill_type="solid")
    summary_fill = PatternFill(start_color="EAE5D9", end_color="EAE5D9", fill_type="solid")

    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    current_row = 1

    # Main Banner
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row + 1, end_column=8)
    title_cell = ws.cell(row=current_row, column=1)
    title_cell.value = f"گزارش کارکرد و کسری خط تولید کارگاه طلای دیلان - {shift_data.get('day_of_week', '')} {shift_data.get('date_shamsi', '')}"
    title_cell.font = title_font
    title_cell.fill = gold_dark_fill
    title_cell.alignment = center_align
    current_row += 3

    # Section 1: اقلام ورودی به کارگاه
    ws.cell(row=current_row, column=1, value="۱. اقلام تحویلی اولیه به کارگاه (بچ‌های ورودی)").font = sub_header_font
    current_row += 1

    batch_headers = ["ردیف", "عنوان کار", "تعداد (عدد)", "وزن کل ورودی (گرم)", "عیار", "توضیحات"]
    for col_idx, text in enumerate(batch_headers, start=1):
        cell = ws.cell(row=current_row, column=col_idx, value=text)
        cell.font = header_font
        cell.fill = gold_header_fill
        cell.alignment = center_align
    current_row += 1

    for idx, b in enumerate(batches, start=1):
        ws.cell(row=current_row, column=1, value=idx).alignment = center_align
        ws.cell(row=current_row, column=2, value=b.get("title", "")).alignment = right_align
        ws.cell(row=current_row, column=3, value=b.get("total_count", 1)).alignment = center_align
        c_weight = ws.cell(row=current_row, column=4, value=round(float(b.get("total_weight", 0.0)), 3))
        c_weight.alignment = center_align
        c_weight.number_format = '0.000'
        ws.cell(row=current_row, column=5, value=b.get("carat", 750)).alignment = center_align
        ws.cell(row=current_row, column=6, value=b.get("notes", "")).alignment = right_align
        current_row += 1

    current_row += 2

    # Section 2: جزئیات مراحل کار و کسری سازندگان
    ws.cell(row=current_row, column=1, value="۲. جدول ثبت مراحل ساخت و کسری‌های خط تولید (نیما، امیر، عطا و...)").font = sub_header_font
    current_row += 1

    task_headers = ["ردیف", "نام سازنده", "مرحله کاری", "عنوان قطعه", "تعداد", "وزن ورودی (گرم)", "وزن خروجی (گرم)", "کسری/افت (گرم)"]
    for col_idx, text in enumerate(task_headers, start=1):
        cell = ws.cell(row=current_row, column=col_idx, value=text)
        cell.font = header_font
        cell.fill = gold_header_fill
        cell.alignment = center_align
    current_row += 1

    stage_fa = {
        "skin": "پوست",
        "polish": "پرداخت",
        "melgat": "ملگات",
        "stripping": "لایه‌برداری",
        "laser": "لیزر",
        "rolling": "نورد",
        "carving": "تراش داخل",
        "wire_solder": "لحیم و مفتول",
        "custom": "سایر"
    }

    tot_in = 0.0
    tot_out = 0.0
    tot_loss = 0.0

    for idx, t in enumerate(tasks, start=1):
        in_w = float(t.get("input_weight", 0.0))
        out_w = float(t.get("output_weight", 0.0))
        loss_w = float(t.get("loss_weight", 0.0))
        tot_in += in_w
        tot_out += out_w
        tot_loss += loss_w

        ws.cell(row=current_row, column=1, value=idx).alignment = center_align
        ws.cell(row=current_row, column=2, value=t.get("craftsman_name", "")).alignment = center_align
        ws.cell(row=current_row, column=3, value=stage_fa.get(t.get("stage", ""), t.get("stage", ""))).alignment = center_align
        ws.cell(row=current_row, column=4, value=t.get("item_name", "")).alignment = right_align
        ws.cell(row=current_row, column=5, value=t.get("count", 1)).alignment = center_align

        c1 = ws.cell(row=current_row, column=6, value=round(in_w, 3))
        c1.alignment = center_align
        c1.number_format = '0.000'

        c2 = ws.cell(row=current_row, column=7, value=round(out_w, 3))
        c2.alignment = center_align
        c2.number_format = '0.000'

        c3 = ws.cell(row=current_row, column=8, value=round(loss_w, 3))
        c3.alignment = center_align
        c3.number_format = '0.000'
        c3.font = loss_font if loss_w < 0 else bold_font
        current_row += 1

    # Task Total Summary
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=5)
    sum_cell = ws.cell(row=current_row, column=1, value="سرجمع مراحل")
    sum_cell.font = bold_font
    sum_cell.alignment = center_align
    sum_cell.fill = summary_fill

    c_tin = ws.cell(row=current_row, column=6, value=round(tot_in, 3))
    c_tin.font = bold_font
    c_tin.alignment = center_align
    c_tin.number_format = '0.000'
    c_tin.fill = summary_fill

    c_tout = ws.cell(row=current_row, column=7, value=round(tot_out, 3))
    c_tout.font = bold_font
    c_tout.alignment = center_align
    c_tout.number_format = '0.000'
    c_tout.fill = summary_fill

    c_tloss = ws.cell(row=current_row, column=8, value=round(tot_loss, 3))
    c_tloss.font = loss_font
    c_tloss.alignment = center_align
    c_tloss.number_format = '0.000'
    c_tloss.fill = summary_fill
    current_row += 2

    # Section 3: رویدادها و افت به سوآله
    if incidents:
        ws.cell(row=current_row, column=1, value="۳. رویدادها، ریزش‌ها و افت به سوآله").font = sub_header_font
        current_row += 1
        inc_headers = ["ردیف", "نام استادکار", "شرح رویداد / قطعه", "وزن اولیه (گرم)", "مقصد سوآله", "وزن ثانویه", "توضیحات"]
        for col_idx, text in enumerate(inc_headers, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=text)
            cell.font = header_font
            cell.fill = gold_header_fill
            cell.alignment = center_align
        current_row += 1

        for idx, inc in enumerate(incidents, start=1):
            ws.cell(row=current_row, column=1, value=idx).alignment = center_align
            ws.cell(row=current_row, column=2, value=inc.get("craftsman_name", "")).alignment = center_align
            ws.cell(row=current_row, column=3, value=inc.get("title", "")).alignment = right_align
            c_w = ws.cell(row=current_row, column=4, value=round(float(inc.get("weight", 0.0)), 3))
            c_w.alignment = center_align
            c_w.number_format = '0.000'
            ws.cell(row=current_row, column=5, value=inc.get("target_bucket", "")).alignment = center_align
            w_after = inc.get("weight_after")
            c_wa = ws.cell(row=current_row, column=6, value=round(float(w_after), 3) if w_after is not None else "-")
            c_wa.alignment = center_align
            if w_after is not None:
                c_wa.number_format = '0.000'
            ws.cell(row=current_row, column=7, value=inc.get("notes", "")).alignment = right_align
            current_row += 1
        current_row += 2

    # Section 4: باکس خلاصه نهایی روزانه
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
    box_header = ws.cell(row=current_row, column=1, value="خلاصه آماری شیفت کارگاه (Dilan Summary)")
    box_header.font = bold_font
    box_header.fill = gold_header_fill
    box_header.alignment = center_align
    current_row += 1

    summary_items = [
        ("کسری کل مراحل تولید:", f"{round(tot_loss, 3)} گرم"),
        ("مجموع سوآله و چرم ثبت‌شده:", f"{round(float(shift_data.get('total_swarf', 0.0)), 3)} گرم"),
        ("وضعیت نهایی روز:", shift_data.get("status", "تکمیل شده")),
    ]
    for label, val in summary_items:
        ws.cell(row=current_row, column=1, value=label).font = bold_font
        ws.cell(row=current_row, column=2, value=val).alignment = center_align
        current_row += 1

    apply_table_styles(ws, current_row, 8)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
