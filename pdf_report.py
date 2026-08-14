"""
Builds a downloadable PDF summary of one participant's results, offered as a
download button on the results screen.

The layout mirrors the "Overview" / "Next Steps" tabs in app.py as closely as
a static PDF allows: a native vector-drawn radar chart (same geometry as the
Plotly chart in render_radar — drawn with fpdf2 primitives rather than
exporting the Plotly figure, so the PDF has no dependency on a headless
browser/Kaleido at render time), a bordered KPI table, and colored
current/target level cards for the top recommendations.

Typography is Montserrat (bundled under fonts/, SIL Open Font License) at a
fixed two-size system — 12pt body, 14pt bold titles — with 2.54cm margins on
all four sides. Colors come from the brand palette in _palette below.

Framework content (dimension levels, solutions) is read straight from the
workbook via data_loader.py, exactly like app.py; the ranking/solution-pick
logic is duplicated from app.py rather than imported, to avoid a circular
import (app.py imports this module).
"""

from __future__ import annotations

import math
import os

from fpdf import FPDF

import data_loader as dl
from translations import (
    DIMENSION_NAMES,
    DIMENSION_PRIORITY,
    FALLBACK_SOLUTIONS,
    KPI_DESCRIPTIONS,
    KPI_DIMENSIONS,
    KPI_LABELS,
    t,
    translate_fw,
)

# ===========================================================================
# Brand palette
# ===========================================================================
RED_RGB = (253, 2, 0)          # fd0200 — MVS benchmark line
GREEN_RGB = (141, 199, 63)     # 8dc73f — "next target" accent
NAVY_RGB = (0, 64, 142)        # 00408e — primary / titles / current-state line
SKY_RGB = (49, 188, 235)       # 31bceb — "current level" accent
GRAY_BG_RGB = (219, 218, 216)  # dbdad8 — neutral fills

PRIMARY_RGB = NAVY_RGB
REFERENCE_RED_RGB = RED_RGB
BODY_TEXT_RGB = (35, 35, 35)
GRAY_RGB = (105, 103, 101)
LIGHT_FILL_RGB = GRAY_BG_RGB
BORDER_GRAY_RGB = (188, 186, 184)
RADAR_TRACK_RGB = (203, 201, 199)
NOT_ASSESSED_RGB = (150, 150, 150)

PALE_SKY_RGB = (223, 246, 252)
GREEN_BG_RGB = (234, 244, 219)
GREEN_TEXT_RGB = (64, 96, 27)

# ===========================================================================
# Typography — Montserrat, two sizes only: 12pt body, 14pt bold titles.
# ===========================================================================
FONT_FAMILY = "Montserrat"
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_FILES = {
    "": os.path.join(FONT_DIR, "Montserrat-Regular.ttf"),
    "B": os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
    "I": os.path.join(FONT_DIR, "Montserrat-Italic.ttf"),
}
BODY_SIZE = 12
TITLE_SIZE = 14

# ===========================================================================
# Page geometry — 2.54cm (1 in) margins on all four sides.
# ===========================================================================
PAGE_WIDTH = 210
PAGE_HEIGHT = 297
MARGIN = 25.4
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN


def _safe(text: str) -> str:
    """Montserrat covers the full Latin-1 range plus the typographic glyphs
    (—, arrows) used in the app's UI strings, so this mainly guards against
    emoji and other characters the font simply doesn't ship."""
    if not text:
        return ""
    text = text.replace("🛫", "").replace("ℹ️", "").replace("✅", "-").replace("**", "")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        text = text.encode("ascii", "ignore").decode("ascii")
    return text


def _top_recommendations(answers: dict) -> list[dict]:
    """Same ranking as app.get_top_recommendations."""
    assessed = [(d, s) for d, s in answers.items() if s > 0]
    ranked = sorted(assessed, key=lambda ds: (ds[1], -DIMENSION_PRIORITY[ds[0]]))
    top = ranked[:3]
    return [
        {"dimension": d, "current": s, "target": min(s + 1, 5), "mastered": s == 5}
        for d, s in top
    ]


def _solutions_for(framework: dict, dim: str, target_level: int) -> list[dict]:
    """Same top-up logic as app.get_solutions_for_target."""
    solutions_bank = dl.load_workbook_data()["solutions_bank"]
    sols = list(framework[dim]["solutions"].get(target_level, []))
    seen_names = {s["name"] for s in sols}

    if len(sols) < 3:
        for name in FALLBACK_SOLUTIONS.get(dim, []):
            if name not in seen_names:
                sols.append({"name": name, "vp": None})
                seen_names.add(name)
            if len(sols) >= 3:
                break

    if len(sols) < 3:
        for lvl in sorted(framework[dim]["solutions"].keys()):
            if lvl == target_level:
                continue
            for s in framework[dim]["solutions"][lvl]:
                if s["name"] not in seen_names:
                    sols.append(s)
                    seen_names.add(s["name"])
                if len(sols) >= 3:
                    break
            if len(sols) >= 3:
                break

    out = []
    for s in sols[:5]:
        bank_entry = solutions_bank.get(s["name"], {})
        vp = s.get("vp") or bank_entry.get("vp") or ""
        out.append({"name": s["name"], "vp": vp})
    return out


class _ReportPDF(FPDF):
    def header(self) -> None:  # fpdf2 hook
        pass

    def footer(self) -> None:  # fpdf2 hook — stays inside the bottom margin
        self.set_y(-MARGIN + 4)
        self.set_font(FONT_FAMILY, "", BODY_SIZE - 3)
        self.set_text_color(*GRAY_RGB)
        self.cell(0, 6, f"{self.page_no()}", align="C")


def _register_fonts(pdf: FPDF) -> None:
    for style, path in FONT_FILES.items():
        pdf.add_font(FONT_FAMILY, style, path)


def _ensure_space(pdf: FPDF, needed_h: float) -> None:
    """Manual drawing (line/rect/ellipse) doesn't trigger fpdf2's automatic
    page break, so blocks built from those primitives must check remaining
    space themselves before they start drawing."""
    if pdf.get_y() + needed_h > pdf.page_break_trigger:
        pdf.add_page()


def _mc(pdf: FPDF, w: float, h: float, text: str, **kwargs) -> None:
    """multi_cell wrapper defaulting to left-aligned text that always lands
    back at the left margin — fpdf2's own defaults are justified text that
    parks the cursor at the cell's right edge, which silently drifts every
    block that calls multi_cell more than once in a row off the page."""
    kwargs.setdefault("align", "L")
    kwargs.setdefault("new_x", "LMARGIN")
    kwargs.setdefault("new_y", "NEXT")
    pdf.multi_cell(w, h, text, **kwargs)


def _section_title(pdf: FPDF, text: str) -> None:
    pdf.ln(3)
    pdf.set_font(FONT_FAMILY, "B", TITLE_SIZE)
    pdf.set_text_color(*NAVY_RGB)
    pdf.cell(0, 8, _safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*BODY_TEXT_RGB)
    pdf.ln(1)


# ===========================================================================
# Radar chart — drawn with fpdf2 vector primitives so it needs no headless
# browser / Kaleido at render time, but mirrors render_radar's geometry
# (clockwise from 12 o'clock) and legend, in the brand palette.
# ===========================================================================
def _draw_radar_chart(pdf: FPDF, lang: str, answers: dict, framework: dict) -> None:
    dims = dl.DIMENSIONS
    n = len(dims)
    radius = 32.0
    cx = MARGIN + CONTENT_WIDTH / 2
    top_pad = 4
    _ensure_space(pdf, top_pad + radius * 2 + 26)
    cy = pdf.get_y() + top_pad + radius + 8

    def angle_for(i: int) -> float:
        return math.radians(90 - (360 / n) * i)

    def pt(i: int, value: float, max_val: float = 5) -> tuple[float, float]:
        r = radius * (value / max_val)
        a = angle_for(i)
        return (cx + r * math.cos(a), cy - r * math.sin(a))

    pdf.set_draw_color(*RADAR_TRACK_RGB)
    pdf.set_line_width(0.25)
    for ring in range(1, 6):
        pts = [pt(i, ring) for i in range(n)]
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            pdf.line(x1, y1, x2, y2)
    for i in range(n):
        x, y = pt(i, 5)
        pdf.line(cx, cy, x, y)

    def _draw_polygon(values: list[float], color: tuple[int, int, int]) -> list[tuple[float, float]]:
        pts = [pt(i, values[i]) for i in range(n)]
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.7)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            pdf.line(x1, y1, x2, y2)
        return pts

    mvs_vals = [framework[d]["mvs"] for d in dims]
    mvs_pts = _draw_polygon(mvs_vals, REFERENCE_RED_RGB)
    pdf.set_fill_color(*REFERENCE_RED_RGB)
    for x, y in mvs_pts:
        pdf.ellipse(x - 1.3, y - 1.3, 2.6, 2.6, style="F")

    cur_vals = [answers.get(d, 0) for d in dims]
    cur_pts = _draw_polygon(cur_vals, PRIMARY_RGB)
    for i, (x, y) in enumerate(cur_pts):
        color = NOT_ASSESSED_RGB if cur_vals[i] == 0 else PRIMARY_RGB
        pdf.set_fill_color(*color)
        pdf.ellipse(x - 1.3, y - 1.3, 2.6, 2.6, style="F")

    # Axis labels
    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE - 2)
    pdf.set_text_color(*NAVY_RGB)
    for i, dim in enumerate(dims):
        lx, ly = pt(i, 6.7)
        name = _safe(DIMENSION_NAMES[lang][dim])
        w = pdf.get_string_width(name) + 2
        pdf.set_xy(lx - w / 2, ly - 2.6)
        pdf.cell(w, 5.2, name, align="C")
    pdf.set_text_color(*BODY_TEXT_RGB)

    # Legend
    legend_y = cy + radius + 11
    pdf.set_font(FONT_FAMILY, "", BODY_SIZE - 2)
    legend_items = [(t(lang, "series_mvs"), REFERENCE_RED_RGB), (t(lang, "series_current"), PRIMARY_RGB)]
    swatch, gap, item_gap = 3.6, 2, 12
    widths = [swatch + gap + pdf.get_string_width(_safe(txt)) + 2 for txt, _ in legend_items]
    total_w = sum(widths) + item_gap * (len(legend_items) - 1)
    x = cx - total_w / 2
    for (txt, color), w in zip(legend_items, widths):
        pdf.set_fill_color(*color)
        pdf.rect(x, legend_y + 0.8, swatch, swatch, style="F")
        pdf.set_xy(x + swatch + gap, legend_y)
        pdf.cell(w, 5.5, _safe(txt))
        x += w + item_gap

    pdf.set_y(legend_y + 9)


# ===========================================================================
# KPI improvement table — real bordered table (dynamic row heights) matching
# the bordered HTML table in the app.
# ===========================================================================
def _draw_kpi_table(pdf: FPDF, lang: str, answers: dict, framework: dict, food_category: str) -> None:
    savings = dl.savings_row_for_category(dl.load_workbook_data()["mvs_savings"], food_category)
    col1_w = CONTENT_WIDTH * 0.62
    col2_w = CONTENT_WIDTH - col1_w
    inner_pad = 2.6
    label_h, desc_h, row_pad = 5.8, 5.2, 2.8

    _ensure_space(pdf, 11)
    pdf.set_fill_color(*LIGHT_FILL_RGB)
    pdf.set_draw_color(*BORDER_GRAY_RGB)
    pdf.set_line_width(0.2)
    header_y = pdf.get_y()
    pdf.rect(MARGIN, header_y, CONTENT_WIDTH, 9, style="DF")
    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
    pdf.set_text_color(*NAVY_RGB)
    pdf.set_xy(MARGIN + inner_pad, header_y + 1.8)
    pdf.cell(col1_w - inner_pad, 5.5, _safe(t(lang, "savings_kpi_col")))
    pdf.set_xy(MARGIN + col1_w + inner_pad, header_y + 1.8)
    pdf.cell(col2_w - inner_pad, 5.5, _safe(t(lang, "savings_value_col")))
    pdf.set_y(header_y + 9)

    for kpi in ["oee", "quality", "energy", "stock"]:
        relevant = KPI_DIMENSIONS[kpi]
        assessed_relevant = [d for d in relevant if answers.get(d, 0) > 0]
        if not assessed_relevant:
            value = t(lang, "not_assessed_kpi")
        elif all(answers[d] >= framework[d]["mvs"] for d in assessed_relevant):
            value = t(lang, "already_at_mvs")
        else:
            value = savings.get(kpi, "")

        label = _safe(KPI_LABELS[lang][kpi])
        desc = _safe(KPI_DESCRIPTIONS[lang][kpi])
        value_safe = _safe(str(value))

        pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
        label_lines = pdf.multi_cell(col1_w - 2 * inner_pad, label_h, label, split_only=True)
        pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
        desc_lines = pdf.multi_cell(col1_w - 2 * inner_pad, desc_h, desc, split_only=True)
        pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
        value_lines = pdf.multi_cell(col2_w - 2 * inner_pad, label_h, value_safe, split_only=True)
        col1_h = len(label_lines) * label_h + len(desc_lines) * desc_h
        col2_h = len(value_lines) * label_h
        row_h = max(col1_h, col2_h) + 2 * row_pad

        _ensure_space(pdf, row_h)
        row_y = pdf.get_y()
        pdf.set_draw_color(*BORDER_GRAY_RGB)
        pdf.set_line_width(0.2)
        pdf.rect(MARGIN, row_y, CONTENT_WIDTH, row_h, style="D")
        pdf.line(MARGIN + col1_w, row_y, MARGIN + col1_w, row_y + row_h)

        pdf.set_xy(MARGIN + inner_pad, row_y + row_pad)
        pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
        pdf.set_text_color(*BODY_TEXT_RGB)
        _mc(pdf, col1_w - 2 * inner_pad, label_h, label, new_x="LEFT")
        pdf.set_x(MARGIN + inner_pad)
        pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
        pdf.set_text_color(*GRAY_RGB)
        _mc(pdf, col1_w - 2 * inner_pad, desc_h, desc, new_x="LEFT")

        pdf.set_xy(MARGIN + col1_w + inner_pad, row_y + row_pad)
        pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
        pdf.set_text_color(*NAVY_RGB)
        _mc(pdf, col2_w - 2 * inner_pad, label_h, value_safe, new_x="LEFT")
        pdf.set_text_color(*BODY_TEXT_RGB)

        pdf.set_y(row_y + row_h)


# ===========================================================================
# Next-steps current/target cards — colored, bordered, rounded boxes mirror
# the sky-blue "Current" / green "Next Target" cards on the results page.
# ===========================================================================
def _card_content_height(pdf: FPDF, card_w: float, label: str, lvl_num: int, name: str, desc: str) -> float:
    pad = 4
    w_text = card_w - 2 * pad
    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
    h1 = len(pdf.multi_cell(w_text, 5.6, _safe(f"{label}: {lvl_num}"), split_only=True)) * 5.6
    h2 = len(pdf.multi_cell(w_text, 5.3, _safe(name), split_only=True)) * 5.3
    pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
    h3 = len(pdf.multi_cell(w_text, 5.0, _safe(desc), split_only=True)) * 5.0
    return h1 + h2 + h3 + 2 * pad


def _draw_level_card(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    label: str, lvl_num: int, name: str, desc: str,
    bg: tuple[int, int, int], border: tuple[int, int, int], text_color: tuple[int, int, int],
) -> None:
    pdf.set_fill_color(*bg)
    pdf.set_draw_color(*border)
    pdf.set_line_width(0.6)
    pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2.5)

    pad = 4
    w_text = w - 2 * pad
    pdf.set_text_color(*text_color)
    pdf.set_xy(x + pad, y + pad)
    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
    _mc(pdf, w_text, 5.6, _safe(f"{label}: {lvl_num}"), new_x="LEFT")
    pdf.set_x(x + pad)
    _mc(pdf, w_text, 5.3, _safe(name), new_x="LEFT")
    pdf.set_x(x + pad)
    pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
    _mc(pdf, w_text, 5.0, _safe(desc), new_x="LEFT")
    pdf.set_text_color(*BODY_TEXT_RGB)


def _draw_current_target_cards(pdf: FPDF, lang: str, dim: str, rec: dict, framework: dict) -> None:
    card_gap = 8
    card_w = (CONTENT_WIDTH - card_gap) / 2
    current_info = framework[dim]["levels"].get(rec["current"])
    target_info = framework[dim]["levels"].get(rec["target"])

    h_current = h_target = 0.0
    if current_info:
        h_current = _card_content_height(
            pdf, card_w, t(lang, "reco_current_label"), rec["current"],
            translate_fw(lang, current_info["name"]), translate_fw(lang, current_info["description"]),
        )
    if target_info:
        h_target = _card_content_height(
            pdf, card_w, t(lang, "reco_target_label"), rec["target"],
            translate_fw(lang, target_info["name"]), translate_fw(lang, target_info["description"]),
        )
    card_h = max(h_current, h_target, 18)

    _ensure_space(pdf, card_h + 4)
    y = pdf.get_y()
    if current_info:
        _draw_level_card(
            pdf, MARGIN, y, card_w, card_h,
            t(lang, "reco_current_label"), rec["current"],
            translate_fw(lang, current_info["name"]), translate_fw(lang, current_info["description"]),
            PALE_SKY_RGB, SKY_RGB, NAVY_RGB,
        )
    if target_info:
        x2 = MARGIN + card_w + card_gap
        _draw_level_card(
            pdf, x2, y, card_w, card_h,
            t(lang, "reco_target_label"), rec["target"],
            translate_fw(lang, target_info["name"]), translate_fw(lang, target_info["description"]),
            GREEN_BG_RGB, GREEN_RGB, GREEN_TEXT_RGB,
        )
        pdf.set_draw_color(*GRAY_RGB)
        pdf.set_line_width(0.4)
        ay = y + card_h / 2
        pdf.line(MARGIN + card_w + 1.5, ay, x2 - 1.5, ay)

    pdf.set_y(y + card_h + 6)


def build_results_pdf(
    lang: str, profile: dict, answers: dict, framework: dict, food_category: str
) -> bytes:
    pdf = _ReportPDF(format="A4", unit="mm")
    _register_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_page()

    # Title block (no full-bleed banner — everything stays inside the margins)
    pdf.set_font(FONT_FAMILY, "B", TITLE_SIZE)
    pdf.set_text_color(*NAVY_RGB)
    _mc(pdf, CONTENT_WIDTH, 7, _safe(t(lang, "title")))
    pdf.set_draw_color(*NAVY_RGB)
    pdf.set_line_width(0.6)
    pdf.line(MARGIN, pdf.get_y() + 1, MARGIN + CONTENT_WIDTH, pdf.get_y() + 1)
    pdf.ln(5)

    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
    pdf.set_text_color(*BODY_TEXT_RGB)
    _mc(
        pdf, CONTENT_WIDTH, 6.5,
        _safe(t(lang, "results_for", name=profile.get("name", ""), company=profile.get("company", ""))),
    )

    # --- Radar chart: current state vs. MVS ---------------------------------
    _section_title(pdf, t(lang, "radar_title").replace("#", "").strip())
    _draw_radar_chart(pdf, lang, answers, framework)

    for dim in dl.DIMENSIONS:
        score = answers.get(dim, 0)
        mvs = framework[dim]["mvs"]
        if score == 0:
            level_text = t(lang, "level0_label")
        else:
            level_name = translate_fw(lang, framework[dim]["levels"][score]["name"])
            level_text = f"{score}/5 - {level_name}"
        pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
        pdf.set_text_color(*GRAY_RGB)
        _mc(
            pdf, CONTENT_WIDTH, 5.6,
            _safe(f"{DIMENSION_NAMES[lang][dim]} - {t(lang, 'series_current')}: {level_text} | {t(lang, 'series_mvs')}: {mvs}/5"),
        )
    pdf.set_text_color(*BODY_TEXT_RGB)

    # --- MVS savings opportunity ---------------------------------------------
    _section_title(pdf, t(lang, "savings_title").replace("#", "").strip())
    pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
    pdf.set_text_color(*GRAY_RGB)
    _mc(pdf, CONTENT_WIDTH, 5.8, _safe(t(lang, "savings_caption", category=food_category)))
    pdf.set_text_color(*BODY_TEXT_RGB)
    pdf.ln(1)

    _draw_kpi_table(pdf, lang, answers, framework, food_category)

    pdf.ln(2)
    pdf.set_font(FONT_FAMILY, "I", BODY_SIZE - 1)
    pdf.set_text_color(*GRAY_RGB)
    _mc(pdf, CONTENT_WIDTH, 4.8, _safe(t(lang, "savings_footnote")))
    pdf.set_text_color(*BODY_TEXT_RGB)

    # --- Next steps -----------------------------------------------------------
    top = _top_recommendations(answers)
    if top:
        _section_title(pdf, t(lang, "reco_title").replace("#", "").strip())
        for idx, rec in enumerate(top):
            dim = rec["dimension"]
            _ensure_space(pdf, 16)
            pdf.set_fill_color(*LIGHT_FILL_RGB)
            pdf.set_font(FONT_FAMILY, "B", TITLE_SIZE)
            pdf.set_text_color(*NAVY_RGB)
            _mc(pdf, CONTENT_WIDTH, 8, _safe(DIMENSION_NAMES[lang][dim]), fill=True)
            pdf.set_text_color(*BODY_TEXT_RGB)
            pdf.ln(1.5)

            if rec["mastered"]:
                pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
                _mc(pdf, CONTENT_WIDTH, 6.5, _safe(t(lang, "reco_mastered_title")))
                pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
                _mc(pdf, CONTENT_WIDTH, 5.8, _safe(translate_fw(lang, framework[dim]["next_step"])))
            else:
                _draw_current_target_cards(pdf, lang, dim, rec, framework)

                solutions = _solutions_for(framework, dim, rec["target"])
                if solutions:
                    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
                    _mc(pdf, CONTENT_WIDTH, 5.8, _safe(t(lang, "reco_solutions_heading")))
                    pdf.ln(0.5)
                for s in solutions:
                    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
                    _mc(pdf, CONTENT_WIDTH, 5.8, _safe(f"- {s['name']}"))
                    if s["vp"]:
                        pdf.set_font(FONT_FAMILY, "", BODY_SIZE)
                        pdf.set_text_color(*GRAY_RGB)
                        _mc(pdf, CONTENT_WIDTH, 5.4, _safe(translate_fw(lang, s["vp"])))
                        pdf.set_text_color(*BODY_TEXT_RGB)

            if idx < len(top) - 1:
                pdf.ln(2.5)
                _ensure_space(pdf, 5)
                y = pdf.get_y()
                pdf.set_draw_color(*BORDER_GRAY_RGB)
                pdf.set_line_width(0.2)
                pdf.line(MARGIN, y, PAGE_WIDTH - MARGIN, y)
                pdf.ln(4.5)
            else:
                pdf.ln(3)

    return bytes(pdf.output())
