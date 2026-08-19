"""
Builds a downloadable PDF summary of one participant's results, offered as a
download button on the results screen.

The layout mirrors the "Overview" / "Next Steps" tabs in app.py as closely as
a static PDF allows: a native vector-drawn radar chart (same geometry as the
Plotly chart in render_radar — drawn with fpdf2 primitives rather than
exporting the Plotly figure, so the PDF has no dependency on a headless
browser/Kaleido at render time), a bordered KPI table, colored current/target
level cards for the top recommendations, and a customer-stories section.

Typography is core Helvetica (no embedded font — smaller file, no extra
assets) at a compact, per-element size scale so the Overview page (radar +
per-dimension summary + savings table) and the Next Steps page each fit on a
single sheet. Margins are 2.54cm on all four sides; colors come from the
brand palette below.

Framework content (dimension levels, solutions) is read straight from the
workbook via data_loader.py, exactly like app.py; the ranking/solution-pick
and customer-story dedup logic is duplicated from app.py rather than
imported, to avoid a circular import (app.py imports this module).
"""

from __future__ import annotations

import math

from fpdf import FPDF

import data_loader as dl
from translations import (
    DIMENSION_NAMES,
    DIMENSION_PRIORITY,
    FALLBACK_SOLUTIONS,
    KPI_DESCRIPTIONS,
    KPI_DIMENSIONS,
    KPI_LABELS,
    food_category_label,
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
GRAY_BG_RGB = (248, 249, 250)  # F8F9FA — neutral fills (category bars, contact box)

PRIMARY_RGB = NAVY_RGB
REFERENCE_RED_RGB = RED_RGB
AUDIENCE_RGB = GREEN_RGB       # audience-average radar series (distinct from MVS red / current navy)
BODY_TEXT_RGB = (35, 35, 35)
GRAY_RGB = (105, 103, 101)
LIGHT_FILL_RGB = GRAY_BG_RGB
CONTACT_BG_RGB = GRAY_BG_RGB
BORDER_GRAY_RGB = (188, 186, 184)
RADAR_TRACK_RGB = (203, 201, 199)
NOT_ASSESSED_RGB = (150, 150, 150)

PALE_SKY_RGB = (223, 246, 252)
GREEN_BG_RGB = (234, 244, 219)
GREEN_TEXT_RGB = (64, 96, 27)

FONT_FAMILY = "helvetica"

# ===========================================================================
# Page geometry — 2.54cm (1 in) margins on all four sides.
# ===========================================================================
PAGE_WIDTH = 210
PAGE_HEIGHT = 297
MARGIN = 25.4
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

CONTACT_EMAIL = "contacto@factoryos.com"  # placeholder — swap for the real address
NEXT_STEPS_TITLE = {
    "en": "Next steps by priority category and recommended solutions",
    "es": "Próximos pasos por categoría priorizada y soluciones recomendadas",
}
CONTACT_BOX_TEXT = {
    "en": f"For more information on implementing these solutions with FactoryOS, write to {CONTACT_EMAIL}",
    "es": f"Para más información sobre cómo implementar estas soluciones con FactoryOS escribe a {CONTACT_EMAIL}",
}
STORIES_LINK_HINT = {
    "en": "Tip: Cmd/Ctrl + click a link to open it in a new tab without losing this PDF.",
    "es": "Tip: usa Cmd/Ctrl + clic sobre un enlace para abrirlo en una pestaña nueva sin perder este PDF.",
}


def _safe(text: str) -> str:
    """Core Helvetica only supports Latin-1 — swap the handful of
    non-Latin-1 glyphs the app's UI strings use (arrows, checkmarks, emoji,
    markdown bold markers) for ASCII, then drop anything else that still
    doesn't fit rather than raising mid-render."""
    if not text:
        return ""
    text = (
        text.replace("→", "->")
        .replace("←", "<-")
        .replace("✅", "-")
        .replace("🛫", "")
        .replace("ℹ️", "")
        .replace("—", " - ")
        .replace("–", "-")
        .replace("**", "")
    )
    return text.encode("latin-1", "ignore").decode("latin-1")


def _top_recommendations(answers: dict) -> list[dict]:
    """Same ranking as app.get_top_recommendations."""
    assessed = [(d, s) for d, s in answers.items() if s > 0]
    ranked = sorted(assessed, key=lambda ds: (ds[1], -DIMENSION_PRIORITY[ds[0]]))
    top = ranked[:3]
    return [
        {"dimension": d, "current": s, "target": min(s + 1, 5), "mastered": s == 5}
        for d, s in top
    ]


def _solutions_for(framework: dict, dim: str, target_level: int, limit: int = 3) -> list[dict]:
    """Same top-up logic as app.get_solutions_for_target, capped at `limit`
    (3 here, vs. up to 5 on the results page) to keep the PDF's Next Steps
    section to a single page."""
    solutions_bank = dl.load_workbook_data()["solutions_bank"]
    sols = list(framework[dim]["solutions"].get(target_level, []))
    seen_names = {s["name"] for s in sols}

    if len(sols) < limit:
        for name in FALLBACK_SOLUTIONS.get(dim, []):
            if name not in seen_names:
                sols.append({"name": name, "vp": None})
                seen_names.add(name)
            if len(sols) >= limit:
                break

    if len(sols) < limit:
        for lvl in sorted(framework[dim]["solutions"].keys()):
            if lvl == target_level:
                continue
            for s in framework[dim]["solutions"][lvl]:
                if s["name"] not in seen_names:
                    sols.append(s)
                    seen_names.add(s["name"])
                if len(sols) >= limit:
                    break
            if len(sols) >= limit:
                break

    out = []
    for s in sols[:limit]:
        bank_entry = solutions_bank.get(s["name"], {})
        vp = s.get("vp") or bank_entry.get("vp") or ""
        out.append({"name": s["name"], "vp": vp})
    return out


def _top_stories(answers: dict, food_category: str, max_total: int = 6) -> list[dict]:
    """Same ranking + cross-dimension dedup as app.render_stories_tab."""
    all_stories = dl.load_workbook_data()["customer_stories"]
    top = _top_recommendations(answers)
    seen: set[str] = set()
    picked: list[dict] = []
    for rec in top:
        if len(picked) >= max_total:
            break
        dim = rec["dimension"]
        bucket = "1-2" if rec["current"] <= 2 else ("3" if rec["current"] == 3 else "4-5")
        candidates = [s for s in all_stories if s["dimension"] == dim and s["customer"] not in seen]

        def _score(s: dict) -> tuple:
            cat_match = s["food_category"].strip().lower() == food_category.strip().lower()
            bucket_match = s["maturity_bucket"] == bucket
            return (cat_match, bucket_match)

        picked_for_dim = 0
        for s in sorted(candidates, key=_score, reverse=True):
            if s["customer"] in seen:
                continue
            seen.add(s["customer"])
            picked.append(s)
            picked_for_dim += 1
            if picked_for_dim >= 2 or len(picked) >= max_total:
                break
    return picked


class _ReportPDF(FPDF):
    def header(self) -> None:  # fpdf2 hook
        pass

    def footer(self) -> None:  # fpdf2 hook — stays inside the bottom margin
        self.set_y(-MARGIN + 4)
        self.set_font(FONT_FAMILY, "", 8)
        self.set_text_color(*GRAY_RGB)
        self.cell(0, 6, f"{self.page_no()}", align="C")


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
    pdf.ln(2.5)
    pdf.set_font(FONT_FAMILY, "B", 13)
    pdf.set_text_color(*NAVY_RGB)
    _mc(pdf, CONTENT_WIDTH, 6.2, _safe(text))
    pdf.set_text_color(*BODY_TEXT_RGB)
    pdf.ln(0.5)


# ===========================================================================
# Radar chart — drawn with fpdf2 vector primitives so it needs no headless
# browser / Kaleido at render time, but mirrors render_radar's geometry
# (clockwise from 12 o'clock) and legend, in the brand palette.
# ===========================================================================
def _draw_radar_chart(
    pdf: FPDF, lang: str, answers: dict, framework: dict,
    audience_averages: dict | None = None, audience_count: int = 0,
) -> None:
    dims = dl.DIMENSIONS
    n = len(dims)
    radius = 24.0
    cx = MARGIN + CONTENT_WIDTH / 2
    top_pad = 8  # extra breathing room between the section title and the chart
    _ensure_space(pdf, top_pad + radius * 2 + 22)
    cy = pdf.get_y() + top_pad + radius + 7

    def angle_for(i: int) -> float:
        return math.radians(90 - (360 / n) * i)

    def pt(i: int, value: float, max_val: float = 5) -> tuple[float, float]:
        r = radius * (value / max_val)
        a = angle_for(i)
        return (cx + r * math.cos(a), cy - r * math.sin(a))

    pdf.set_draw_color(*RADAR_TRACK_RGB)
    pdf.set_line_width(0.25)
    for ring in range(1, 6):
        r = radius * (ring / 5)
        pdf.ellipse(cx - r, cy - r, 2 * r, 2 * r, style="D")
    for i in range(n):
        x, y = pt(i, 5)
        pdf.line(cx, cy, x, y)

    def _draw_polygon(values: list[float], color: tuple[int, int, int]) -> list[tuple[float, float]]:
        pts = [pt(i, values[i]) for i in range(n)]
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.6)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            pdf.line(x1, y1, x2, y2)
        return pts

    mvs_vals = [framework[d]["mvs"] for d in dims]
    mvs_pts = _draw_polygon(mvs_vals, REFERENCE_RED_RGB)
    pdf.set_fill_color(*REFERENCE_RED_RGB)
    for x, y in mvs_pts:
        pdf.ellipse(x - 1.1, y - 1.1, 2.2, 2.2, style="F")

    has_audience = bool(audience_averages) and audience_count > 0
    if has_audience:
        aud_vals = [audience_averages.get(d, 0) for d in dims]
        aud_pts = _draw_polygon(aud_vals, AUDIENCE_RGB)
        pdf.set_fill_color(*AUDIENCE_RGB)
        for x, y in aud_pts:
            pdf.ellipse(x - 1.1, y - 1.1, 2.2, 2.2, style="F")

    cur_vals = [answers.get(d, 0) for d in dims]
    cur_pts = _draw_polygon(cur_vals, PRIMARY_RGB)
    for i, (x, y) in enumerate(cur_pts):
        color = NOT_ASSESSED_RGB if cur_vals[i] == 0 else PRIMARY_RGB
        pdf.set_fill_color(*color)
        pdf.ellipse(x - 1.1, y - 1.1, 2.2, 2.2, style="F")

    # Axis labels
    pdf.set_font(FONT_FAMILY, "B", 7.5)
    pdf.set_text_color(*NAVY_RGB)
    for i, dim in enumerate(dims):
        lx, ly = pt(i, 6.5)
        name = _safe(DIMENSION_NAMES[lang][dim])
        w = pdf.get_string_width(name) + 2
        pdf.set_xy(lx - w / 2, ly - 2.3)
        pdf.cell(w, 4.6, name, align="C")
    pdf.set_text_color(*BODY_TEXT_RGB)

    # Legend
    legend_y = cy + radius + 9
    pdf.set_font(FONT_FAMILY, "", 8.5)
    legend_items = [(t(lang, "series_mvs"), REFERENCE_RED_RGB)]
    if has_audience:
        legend_items.append(
            (t(lang, "series_audience", count=audience_count), AUDIENCE_RGB)
        )
    legend_items.append((t(lang, "series_current"), PRIMARY_RGB))
    swatch, gap, item_gap = 3.2, 2, 10
    widths = [swatch + gap + pdf.get_string_width(_safe(txt)) + 2 for txt, _ in legend_items]
    total_w = sum(widths) + item_gap * (len(legend_items) - 1)
    x = cx - total_w / 2
    for (txt, color), w in zip(legend_items, widths):
        pdf.set_fill_color(*color)
        pdf.rect(x, legend_y + 0.8, swatch, swatch, style="F")
        pdf.set_xy(x + swatch + gap, legend_y)
        pdf.cell(w, 5, _safe(txt))
        x += w + item_gap

    pdf.set_y(legend_y + 7)


# ===========================================================================
# KPI improvement table — real bordered table (dynamic row heights) matching
# the bordered HTML table in the app.
# ===========================================================================
def _draw_kpi_table(pdf: FPDF, lang: str, answers: dict, framework: dict, food_category: str) -> None:
    savings = dl.savings_row_for_category(dl.load_workbook_data()["mvs_savings"], food_category)
    col1_w = CONTENT_WIDTH * 0.66
    col2_w = CONTENT_WIDTH - col1_w
    inner_pad = 2.2
    label_h, desc_h, row_pad = 4.3, 3.6, 1.7

    _ensure_space(pdf, 9)
    pdf.set_fill_color(*LIGHT_FILL_RGB)
    pdf.set_draw_color(*BORDER_GRAY_RGB)
    pdf.set_line_width(0.2)
    header_y = pdf.get_y()
    pdf.rect(MARGIN, header_y, CONTENT_WIDTH, 7, style="DF")
    pdf.set_font(FONT_FAMILY, "B", 9.5)
    pdf.set_text_color(*NAVY_RGB)
    pdf.set_xy(MARGIN + inner_pad, header_y + 1.4)
    pdf.cell(col1_w - inner_pad, 4.5, _safe(t(lang, "savings_kpi_col")))
    pdf.set_xy(MARGIN + col1_w + inner_pad, header_y + 1.4)
    pdf.cell(col2_w - inner_pad, 4.5, _safe(t(lang, "savings_value_col")))
    pdf.set_y(header_y + 7)

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

        pdf.set_font(FONT_FAMILY, "B", 9.5)
        label_lines = pdf.multi_cell(col1_w - 2 * inner_pad, label_h, label, split_only=True)
        pdf.set_font(FONT_FAMILY, "", 7.8)
        desc_lines = pdf.multi_cell(col1_w - 2 * inner_pad, desc_h, desc, split_only=True)
        pdf.set_font(FONT_FAMILY, "B", 9.5)
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
        pdf.set_font(FONT_FAMILY, "B", 9.5)
        pdf.set_text_color(*BODY_TEXT_RGB)
        _mc(pdf, col1_w - 2 * inner_pad, label_h, label, new_x="LEFT")
        pdf.set_x(MARGIN + inner_pad)
        pdf.set_font(FONT_FAMILY, "", 7.8)
        pdf.set_text_color(*GRAY_RGB)
        _mc(pdf, col1_w - 2 * inner_pad, desc_h, desc, new_x="LEFT")

        pdf.set_xy(MARGIN + col1_w + inner_pad, row_y + row_pad)
        pdf.set_font(FONT_FAMILY, "B", 9.5)
        pdf.set_text_color(*NAVY_RGB)
        _mc(pdf, col2_w - 2 * inner_pad, label_h, value_safe, new_x="LEFT")
        pdf.set_text_color(*BODY_TEXT_RGB)

        pdf.set_y(row_y + row_h)


# ===========================================================================
# Next-steps current/target cards — colored, bordered, rounded boxes mirror
# the sky-blue "Current" / green "Next Target" cards on the results page.
# ===========================================================================
def _card_content_height(pdf: FPDF, card_w: float, label: str, lvl_num: int, name: str, desc: str) -> float:
    pad = 3
    w_text = card_w - 2 * pad
    pdf.set_font(FONT_FAMILY, "B", 9.5)
    h1 = len(pdf.multi_cell(w_text, 4.3, _safe(f"{label}: {lvl_num}"), split_only=True)) * 4.3
    pdf.set_font(FONT_FAMILY, "B", 9.2)
    h2 = len(pdf.multi_cell(w_text, 4.1, _safe(name), split_only=True)) * 4.1
    pdf.set_font(FONT_FAMILY, "", 8)
    h3 = len(pdf.multi_cell(w_text, 3.7, _safe(desc), split_only=True)) * 3.7
    return h1 + h2 + h3 + 2 * pad


def _draw_level_card(
    pdf: FPDF, x: float, y: float, w: float, h: float,
    label: str, lvl_num: int, name: str, desc: str,
    bg: tuple[int, int, int], border: tuple[int, int, int], text_color: tuple[int, int, int],
) -> None:
    pdf.set_fill_color(*bg)
    pdf.set_draw_color(*border)
    pdf.set_line_width(0.5)
    pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)

    pad = 3
    w_text = w - 2 * pad
    pdf.set_text_color(*text_color)
    pdf.set_xy(x + pad, y + pad)
    pdf.set_font(FONT_FAMILY, "B", 9.5)
    _mc(pdf, w_text, 4.3, _safe(f"{label}: {lvl_num}"), new_x="LEFT")
    pdf.set_x(x + pad)
    pdf.set_font(FONT_FAMILY, "B", 9.2)
    _mc(pdf, w_text, 4.1, _safe(name), new_x="LEFT")
    pdf.set_x(x + pad)
    pdf.set_font(FONT_FAMILY, "", 8)
    _mc(pdf, w_text, 3.7, _safe(desc), new_x="LEFT")
    pdf.set_text_color(*BODY_TEXT_RGB)


def _draw_current_target_cards(pdf: FPDF, lang: str, dim: str, rec: dict, framework: dict) -> None:
    card_gap = 6
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
    card_h = max(h_current, h_target, 14)

    _ensure_space(pdf, card_h + 3)
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
        pdf.line(MARGIN + card_w + 1, ay, x2 - 1, ay)

    pdf.set_y(y + card_h + 3.5)


def _draw_contact_box(pdf: FPDF, lang: str) -> None:
    text = _safe(CONTACT_BOX_TEXT[lang])
    pdf.set_font(FONT_FAMILY, "B", 10)
    lines = pdf.multi_cell(CONTENT_WIDTH - 12, 5, text, split_only=True)
    box_h = len(lines) * 5 + 10
    _ensure_space(pdf, box_h + 4)
    y = pdf.get_y()
    pdf.set_fill_color(*CONTACT_BG_RGB)
    pdf.set_draw_color(*NAVY_RGB)
    pdf.set_line_width(0.5)
    pdf.rect(MARGIN, y, CONTENT_WIDTH, box_h, style="DF", round_corners=True, corner_radius=2)
    pdf.set_xy(MARGIN + 6, y + 5)
    pdf.set_text_color(*NAVY_RGB)
    _mc(pdf, CONTENT_WIDTH - 12, 5, text, new_x="LEFT")
    pdf.set_text_color(*BODY_TEXT_RGB)
    pdf.set_y(y + box_h)


def build_results_pdf(
    lang: str, profile: dict, answers: dict, framework: dict, food_category: str,
    audience_averages: dict | None = None, audience_count: int = 0,
) -> bytes:
    pdf = _ReportPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_page()

    # Title block (no full-bleed banner — everything stays inside the margins)
    pdf.set_font(FONT_FAMILY, "B", 15)
    pdf.set_text_color(*NAVY_RGB)
    _mc(pdf, CONTENT_WIDTH, 6.5, _safe(t(lang, "title")))
    pdf.set_draw_color(*NAVY_RGB)
    pdf.set_line_width(0.4)
    pdf.line(MARGIN, pdf.get_y() + 1, MARGIN + CONTENT_WIDTH, pdf.get_y() + 1)
    pdf.ln(3.5)

    pdf.set_font(FONT_FAMILY, "", 12)
    pdf.set_text_color(*BODY_TEXT_RGB)
    _mc(
        pdf, CONTENT_WIDTH, 5.6,
        _safe(t(lang, "results_for", name=profile.get("name", ""), company=profile.get("company", ""))),
    )

    # --- Radar chart: current state vs. MVS ---------------------------------
    _section_title(pdf, t(lang, "radar_title").replace("#", "").strip())
    _draw_radar_chart(pdf, lang, answers, framework, audience_averages, audience_count)

    for dim in dl.DIMENSIONS:
        score = answers.get(dim, 0)
        mvs = framework[dim]["mvs"]
        if score == 0:
            level_text = t(lang, "level0_label")
        else:
            level_name = translate_fw(lang, framework[dim]["levels"][score]["name"])
            level_text = f"{score}/5 - {level_name}"
        line = _safe(
            f"{DIMENSION_NAMES[lang][dim]} - {t(lang, 'series_current')}: {level_text} | {t(lang, 'series_mvs')}: {mvs}/5"
        )
        pdf.set_font(FONT_FAMILY, "", 8.7)
        while pdf.get_string_width(line) > CONTENT_WIDTH and len(line) > 20:
            line = line[:-6].rstrip() + "..."
        pdf.set_text_color(*GRAY_RGB)
        pdf.cell(CONTENT_WIDTH, 4.6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*BODY_TEXT_RGB)
    pdf.ln(3)

    # --- MVS savings opportunity ---------------------------------------------
    _section_title(pdf, t(lang, "savings_title").replace("#", "").strip())
    pdf.set_font(FONT_FAMILY, "", 9)
    pdf.set_text_color(*GRAY_RGB)
    _mc(pdf, CONTENT_WIDTH, 4.6, _safe(t(lang, "savings_caption", category=food_category_label(lang, food_category))))
    pdf.set_text_color(*BODY_TEXT_RGB)
    pdf.ln(0.5)

    _draw_kpi_table(pdf, lang, answers, framework, food_category)

    pdf.ln(1.5)
    pdf.set_font(FONT_FAMILY, "I", 7.5)
    pdf.set_text_color(*GRAY_RGB)
    _mc(pdf, CONTENT_WIDTH, 3.9, _safe(t(lang, "savings_footnote")))
    pdf.set_text_color(*BODY_TEXT_RGB)

    # --- Next steps -------------------------------------------------------------
    top = _top_recommendations(answers)
    if top:
        pdf.add_page()
        _section_title(pdf, NEXT_STEPS_TITLE[lang])
        pdf.ln(3)
        for idx, rec in enumerate(top):
            dim = rec["dimension"]
            bar_h = 8
            _ensure_space(pdf, bar_h + 4)
            bar_y = pdf.get_y()
            pdf.set_fill_color(*LIGHT_FILL_RGB)
            pdf.rect(MARGIN, bar_y, CONTENT_WIDTH, bar_h, style="F", round_corners=True, corner_radius=2)
            pdf.set_xy(MARGIN + 4, bar_y + 1.3)
            pdf.set_font(FONT_FAMILY, "B", 11)
            pdf.set_text_color(*NAVY_RGB)
            pdf.cell(CONTENT_WIDTH - 8, 5.5, _safe(DIMENSION_NAMES[lang][dim]))
            pdf.set_text_color(*BODY_TEXT_RGB)
            pdf.set_y(bar_y + bar_h)
            pdf.ln(1.5)

            if rec["mastered"]:
                pdf.set_font(FONT_FAMILY, "B", 9.5)
                _mc(pdf, CONTENT_WIDTH, 5, _safe(t(lang, "reco_mastered_title")))
                pdf.set_font(FONT_FAMILY, "", 9)
                _mc(pdf, CONTENT_WIDTH, 4.6, _safe(translate_fw(lang, framework[dim]["next_step"])))
            else:
                _draw_current_target_cards(pdf, lang, dim, rec, framework)

                solutions = _solutions_for(framework, dim, rec["target"], limit=3)
                if solutions:
                    pdf.set_font(FONT_FAMILY, "B", 9.5)
                    _mc(pdf, CONTENT_WIDTH, 4.6, _safe(t(lang, "reco_solutions_heading")))
                for s in solutions:
                    pdf.set_font(FONT_FAMILY, "B", 9)
                    _mc(pdf, CONTENT_WIDTH, 4.4, _safe(f"- {s['name']}"))
                    if s["vp"]:
                        pdf.set_font(FONT_FAMILY, "", 8.3)
                        pdf.set_text_color(*GRAY_RGB)
                        _mc(pdf, CONTENT_WIDTH, 4.1, _safe(translate_fw(lang, s["vp"])))
                        pdf.set_text_color(*BODY_TEXT_RGB)

            if idx < len(top) - 1:
                pdf.ln(4)
            else:
                pdf.ln(2)

    # --- Customer stories ---------------------------------------------------
    stories = _top_stories(answers, food_category)
    if stories:
        pdf.add_page()
        _section_title(pdf, t(lang, "stories_title").replace("#", "").strip())
        pdf.set_font(FONT_FAMILY, "I", 8.5)
        pdf.set_text_color(*GRAY_RGB)
        _mc(pdf, CONTENT_WIDTH, 4.2, _safe(STORIES_LINK_HINT[lang]))
        pdf.set_text_color(*BODY_TEXT_RGB)
        pdf.ln(1.5)
        pdf.set_font(FONT_FAMILY, "", 10)
        for s in stories:
            pdf.set_text_color(*NAVY_RGB)
            _mc(pdf, CONTENT_WIDTH, 6, _safe(f"- {s['customer']}"), link=s["url"])
        pdf.set_text_color(*BODY_TEXT_RGB)

    # --- Contact box ----------------------------------------------------------
    pdf.ln(6)
    _draw_contact_box(pdf, lang)

    return bytes(pdf.output())
