"""
At 10,000 Feet — Digital Readiness Assessment
==============================================
Single-file Streamlit app for Foro MX 2026.

Screens (st.session_state["screen"]):
    "welcome" | "profile" | "motivation" | "assessment" | "results"
Language (st.session_state["lang"]): "en" | "es".

Framework content (dimensions, levels, solutions, MVS, customer stories) is
sourced from Digital_readiness_tool_Framework.xlsx via data_loader.py.
Bilingual UI strings and translations of that workbook content live in
translations.py.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime, timezone

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import data_loader as dl
from pdf_report import build_results_pdf
from translations import (
    DIMENSION_ICONS,
    DIMENSION_NAMES,
    DIMENSION_PRIORITY,
    FALLBACK_SOLUTIONS,
    KPI_DESCRIPTIONS,
    KPI_DIMENSIONS,
    KPI_LABELS,
    UI,
    food_category_label,
    t,
    translate_fw,
)

DIMENSIONS: list[str] = dl.DIMENSIONS  # ["strategy", "people", "operations", "connectivity", "intelligence"]

FOOD_CATEGORIES = ["Dairy", "Beverage", "Cheese", "Ice Cream", "Other"]


# ===========================================================================
# STYLE constants — brand palette sampled from the reference radar mockup:
# a medium royal blue for "your results" / primary UI accents, and a warm
# red reserved for the reference/MVS benchmark series.
# ===========================================================================
PRIMARY = "#2D68F4"
ACCENT = "#2D68F4"
REFERENCE_RED = "#E63323"
MVS_COLOR = REFERENCE_RED
NAVY_TEXT = "#1B2E96"
PALE_BLUE = "#DCE6FE"
GREEN_BG = "#E1F5E7"
GREEN_BORDER = "#2E9E4F"
GREEN_TEXT = "#1C6B34"
RADAR_TRACK_COLOR = "#E3E6EA"

# Categorical palette for the audience/live radar (one line per food category).
# Fixed hue order — validated for adjacent-pair colorblind-safe separation.
CATEGORY_COLORS: dict[str, str] = {
    "Dairy": "#2a78d6",       # blue
    "Beverage": "#eb6834",    # orange
    "Cheese": "#1baf7a",      # aqua
    "Ice Cream": "#eda100",   # yellow
    "Other": "#e87ba4",       # magenta
}


# ===========================================================================
# ANALYTICS — persistence
# ===========================================================================
SHEET_HEADER = (
    ["timestamp_iso", "share_data", "name", "company", "email", "food_category", "motivation",
     "investment_approach", "language"]
    + [f"{d}_level" for d in DIMENSIONS]
    + ["assessed_count"]
)

LOCAL_CSV = "submissions_local.csv"


def _has_google_secrets() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "sheet_id" in st.secrets
    except Exception:
        return False


def _get_worksheet():
    """Return a cached gspread worksheet, authenticating once per session.

    Returns None if Google secrets are absent or auth fails.
    """
    if "gs_worksheet" in st.session_state:
        return st.session_state["gs_worksheet"]

    if not _has_google_secrets():
        st.session_state["gs_worksheet"] = None
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(st.secrets["sheet_id"])
        try:
            ws = spreadsheet.worksheet("submissions")
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title="submissions", rows=1000, cols=len(SHEET_HEADER))

        if not ws.get_all_values():
            ws.append_row(SHEET_HEADER, value_input_option="RAW")

        st.session_state["gs_worksheet"] = ws
        return ws
    except Exception as exc:  # noqa: BLE001
        print(f"[analytics] Google Sheets auth failed: {exc}")
        st.session_state["gs_worksheet"] = None
        return None


def build_row(profile: dict, answers: dict, lang: str) -> list:
    """Assemble one analytics row in the fixed column order.

    When the respondent declined to share their data with TetraPak, name/
    company/email/motivation are omitted (blank) but dimension scores are
    still recorded so aggregate Foro MX stats stay complete.
    """
    share_data = profile.get("share_data", True)
    levels = [answers.get(d, 0) for d in DIMENSIONS]
    assessed_count = sum(1 for v in levels if v > 0)
    pii = (
        [profile["name"], profile["company"], profile["email"], profile.get("food_category", ""),
         profile.get("motivation", ""), profile.get("investment_approach", "")]
        if share_data else ["", "", "", profile.get("food_category", ""), "", ""]
    )
    return (
        [datetime.now(timezone.utc).isoformat(), "yes" if share_data else "no"]
        + pii
        + [lang]
        + levels
        + [assessed_count]
    )


def persist_submission(profile: dict, answers: dict, lang: str) -> None:
    """Append one row to Google Sheets, or fall back to local CSV.

    Never raises — analytics must not block the user from their result.
    """
    row = build_row(profile, answers, lang)

    ws = _get_worksheet()
    if ws is not None:
        try:
            ws.append_row(row, value_input_option="RAW")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[analytics] append to Google Sheets failed: {exc}")

    try:
        write_header = not os.path.exists(LOCAL_CSV)
        with open(LOCAL_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(SHEET_HEADER)
            writer.writerow(row)
    except Exception as exc:  # noqa: BLE001
        print(f"[analytics] local CSV fallback failed: {exc}")


@st.cache_data(ttl=10, show_spinner=False)
def _fetch_all_submissions() -> list[dict]:
    if _has_google_secrets():
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(st.secrets["sheet_id"])
            ws = spreadsheet.worksheet("submissions")
            return ws.get_all_records()
        except Exception as exc:  # noqa: BLE001
            print(f"[live] Google Sheets read failed: {exc}")
            return []

    if not os.path.exists(LOCAL_CSV):
        return []
    with open(LOCAL_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _average_by_dimension(rows: list[dict]) -> dict:
    """Average maturity level per dimension across the given submission rows
    (0/not-assessed answers are excluded from each dimension's average).
    Rows with a garbled/non-numeric level (bad test data in the sheet) are
    skipped rather than crashing the whole live view."""
    averages = {}
    for dim in DIMENSIONS:
        col = f"{dim}_level"
        values = []
        for r in rows:
            raw = str(r.get(col, "")).strip()
            if raw in ("", "0"):
                continue
            try:
                values.append(float(raw))
            except ValueError:
                continue
        averages[dim] = round(sum(values) / len(values), 1) if values else 0.0
    return averages


def _compute_live_aggregate() -> dict:
    """Average maturity level per dimension across every submission so far,
    both overall and broken down per food category."""
    rows = _fetch_all_submissions()
    count = len(rows)
    if count == 0:
        return {
            "count": 0,
            "averages": {d: 0.0 for d in DIMENSIONS},
            "by_category": {},
        }

    by_category = {}
    for cat in FOOD_CATEGORIES:
        cat_rows = [r for r in rows if str(r.get("food_category", "")).strip() == cat]
        if cat_rows:
            by_category[cat] = {"count": len(cat_rows), "averages": _average_by_dimension(cat_rows)}

    return {
        "count": count,
        "averages": _average_by_dimension(rows),
        "by_category": by_category,
    }


def _audience_aggregate_for_category(food_category: str) -> dict:
    """Live snapshot of the audience average (per dimension) and respondent
    count for a single food category — used to overlay a third series on the
    results PDF's radar chart at download time."""
    rows = _fetch_all_submissions()
    cat_rows = [r for r in rows if str(r.get("food_category", "")).strip() == food_category]
    if not cat_rows:
        return {"count": 0, "averages": {d: 0.0 for d in DIMENSIONS}}
    return {"count": len(cat_rows), "averages": _average_by_dimension(cat_rows)}


# ===========================================================================
# SESSION STATE INIT
# ===========================================================================
def init_state() -> None:
    st.session_state.setdefault("screen", "welcome")
    st.session_state.setdefault("lang", "en")
    st.session_state.setdefault("profile", {})
    st.session_state.setdefault("dim_index", 0)
    if "answers" not in st.session_state:
        st.session_state["answers"] = {d: 1 for d in DIMENSIONS}
    st.session_state.setdefault("touched_dims", set())


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def scroll_to_top() -> None:
    components.html(
        """
        <script>
            const doc = window.parent.document;
            const selectors = [
                'section.stMain', 'section.main',
                '.stMainBlockContainer',
                'div[data-testid="stAppViewContainer"]',
            ];
            const jump = () => {
                for (const s of selectors) {
                    const el = doc.querySelector(s);
                    if (el) { el.scrollTo(0, 0); }
                }
                window.parent.scrollTo(0, 0);
            };
            jump();
            setTimeout(jump, 50);
        </script>
        """,
        height=0,
    )


def render_language_switcher() -> None:
    _, col = st.columns([6, 1])
    with col:
        st.selectbox(
            "Language",
            options=["en", "es"],
            format_func=lambda x: "🇬🇧 English" if x == "en" else "🇪🇸 Español",
            key="lang",
            label_visibility="collapsed",
        )


# ===========================================================================
# SCREEN 1 — Welcome
# ===========================================================================
def render_welcome() -> None:
    lang = st.session_state["lang"]
    st.title(t(lang, "title"))
    st.markdown(t(lang, "intro1"))

    pillars_line = t(lang, "pillars_prefix") + " · ".join(
        f"**{DIMENSION_NAMES[lang][d]}**" for d in DIMENSIONS
    )
    st.markdown(pillars_line)

    st.markdown(
        '<div style="font-size:1.5rem;font-weight:600;color:#333;margin:6px 0;">'
        f'<span style="font-size:2.0rem;">✍️</span> {t(lang, "step_answer")}'
        ' &nbsp;→&nbsp; '
        f'<span style="font-size:2.0rem;">🧮</span> {t(lang, "step_calculate")}'
        ' &nbsp;→&nbsp; '
        f'<span style="font-size:2.0rem;">📊</span> {t(lang, "step_review")}'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    if st.button(t(lang, "next"), type="primary"):
        st.session_state["screen"] = "profile"
        st.rerun()


# ===========================================================================
# SCREEN 2 — Participant profile
# ===========================================================================
def render_profile() -> None:
    lang = st.session_state["lang"]
    st.subheader(t(lang, "tell_us"))

    profile = st.session_state["profile"]
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input(t(lang, "full_name"), value=profile.get("name", ""), key="in_name")
        email = st.text_input(
            t(lang, "work_email"), value=profile.get("email", ""), key="in_email",
            help=t(lang, "email_help"),
        )
    with col2:
        company = st.text_input(t(lang, "company"), value=profile.get("company", ""), key="in_company")
        food_category = st.selectbox(
            t(lang, "food_category"),
            options=FOOD_CATEGORIES,
            index=FOOD_CATEGORIES.index(profile.get("food_category", "Dairy")) if profile.get("food_category") in FOOD_CATEGORIES else 0,
            format_func=lambda c: food_category_label(lang, c),
            key="in_food_category",
        )

    email_ok = bool(EMAIL_RE.match(email.strip())) if email else False
    if email and not email_ok:
        st.caption(f":red[{t(lang, 'invalid_email')}]")

    all_filled = all(v.strip() for v in (name, company, email))
    can_continue = all_filled and email_ok

    cols = st.columns([1, 3])
    with cols[0]:
        if st.button(t(lang, "back"), key="back_to_welcome_from_profile"):
            st.session_state["screen"] = "welcome"
            st.rerun()
    with cols[1]:
        if st.button(t(lang, "next"), type="primary", disabled=not can_continue):
            st.session_state["profile"] = {
                **profile,
                "name": name.strip(),
                "company": company.strip(),
                "email": email.strip(),
                "food_category": food_category,
                "share_data": True,
            }
            st.session_state["screen"] = "motivation"
            st.rerun()


# ===========================================================================
# SCREEN 2B — Motivation (optional)
# ===========================================================================
def render_motivation() -> None:
    lang = st.session_state["lang"]
    profile = st.session_state["profile"]

    st.subheader(f"{t(lang, 'motivation_question')} {t(lang, 'motivation_optional')}")
    motivation = st.text_area(
        t(lang, "motivation_question"),
        value=profile.get("motivation", ""),
        placeholder=t(lang, "motivation_placeholder"),
        key="in_motivation",
        label_visibility="collapsed",
        height=150,
    )

    st.subheader(f"{t(lang, 'investment_approach_question')} {t(lang, 'motivation_optional')}")
    investment_approach = st.text_area(
        t(lang, "investment_approach_question"),
        value=profile.get("investment_approach", ""),
        placeholder=t(lang, "investment_approach_placeholder"),
        key="in_investment_approach",
        label_visibility="collapsed",
        height=150,
    )

    cols = st.columns([1, 3])
    with cols[0]:
        if st.button(t(lang, "back"), key="back_to_profile_from_motivation"):
            st.session_state["screen"] = "profile"
            st.rerun()
    with cols[1]:
        if st.button(t(lang, "continue"), type="primary"):
            st.session_state["profile"]["motivation"] = motivation.strip()
            st.session_state["profile"]["investment_approach"] = investment_approach.strip()
            st.session_state["screen"] = "assessment"
            st.session_state["dim_index"] = 0
            st.rerun()


# ===========================================================================
# SCREEN 3 — Assessment (one screen per dimension)
# ===========================================================================
_OPTION_CSS = f"""
<style>
div[data-testid="stButton"] button {{
    text-align: left !important;
    justify-content: flex-start !important;
    white-space: normal !important;
    line-height: 1.4 !important;
    padding: 12px 16px !important;
}}
div[data-testid="stButton"] button p {{
    text-align: left !important;
    white-space: normal !important;
}}
div[data-testid="stButton"] button[kind="primary"] * {{
    color: #FFFFFF !important;
}}
</style>
"""


def _level_option_label(lvl_num: int, name: str, description: str) -> str:
    """Markdown label for one level's button: bold '0. Name' header, and — if
    there's a description — a gray line underneath it, all inside a single
    full-width tappable row (large touch target, no dragging needed)."""
    header = f"**{lvl_num}. {name}**"
    if description:
        return f"{header}  \n:gray[{description}]"
    return header


def render_assessment_step() -> None:
    lang = st.session_state["lang"]
    idx = st.session_state["dim_index"]
    dim = DIMENSIONS[idx]
    fw = dl.load_workbook_data()["framework"][dim]

    st.progress((idx + 1) / len(DIMENSIONS))
    st.caption(t(lang, "step_of", step=idx + 1, total=len(DIMENSIONS)))

    st.subheader(f"{DIMENSION_ICONS[dim]} {DIMENSION_NAMES[lang][dim]}")
    st.markdown(f"*{translate_fw(lang, fw['question'])}*")
    st.info(t(lang, "assessment_instruction"))
    st.markdown("")

    # Level 0 ("I don't know / I don't want to answer") is a real option in
    # this same vertical list, alongside levels 1-5 from the framework — not
    # a separate checkbox — so it reads as a real answer rather than an
    # opt-out control bolted onto the side.
    levels_with_zero = {0: {"name": t(lang, "level0_label"), "description": ""}, **fw["levels"]}

    # A vertical stack of full-width, tappable rows — one per level — replaces
    # the horizontal drag-slider. Dragging a small thumb is fiddly on a phone;
    # tapping a big row is not, and every level's title + description stays
    # visible at once instead of only the one under the thumb.
    st.markdown(_OPTION_CSS, unsafe_allow_html=True)
    current_answer = st.session_state["answers"][dim]
    dim_touched = dim in st.session_state["touched_dims"]
    for lvl_num in sorted(levels_with_zero.keys()):
        level_info = levels_with_zero[lvl_num]
        name = translate_fw(lang, level_info["name"])
        desc = translate_fw(lang, level_info["description"])
        is_selected = dim_touched and lvl_num == current_answer
        if st.button(
            _level_option_label(lvl_num, name, desc),
            key=f"opt_{dim}_{lvl_num}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state["answers"][dim] = lvl_num
            st.session_state["touched_dims"].add(dim)
            st.rerun()

    st.divider()
    cols = st.columns([1, 3])
    with cols[0]:
        if st.button(t(lang, "back"), key=f"back_{dim}"):
            if idx == 0:
                st.session_state["screen"] = "motivation"
            else:
                st.session_state["dim_index"] -= 1
            st.rerun()
    with cols[1]:
        is_last = idx == len(DIMENSIONS) - 1
        label = t(lang, "calc_score") if is_last else t(lang, "next")
        if st.button(label, type="primary"):
            if is_last:
                persist_submission(st.session_state["profile"], st.session_state["answers"], lang)
                st.session_state["screen"] = "results"
                st.session_state["scroll_top"] = True
            else:
                st.session_state["dim_index"] += 1
            st.rerun()


# ===========================================================================
# RECOMMENDATION ENGINE (shared by Tab 2 and Tab 3)
# ===========================================================================
def get_top_recommendations(answers: dict) -> list[dict]:
    """Top-3 lowest-scoring assessed dimensions, tie-broken by
    DIMENSION_PRIORITY (Strategy > Operations > Connectivity > People >
    Intelligence). Dimensions marked 0/not-assessed are excluded."""
    assessed = [(d, s) for d, s in answers.items() if s > 0]
    ranked = sorted(assessed, key=lambda ds: (ds[1], -DIMENSION_PRIORITY[ds[0]]))
    top = ranked[:3]
    out = []
    for dim, score in top:
        out.append({"dimension": dim, "current": score, "target": min(score + 1, 5), "mastered": score == 5})
    return out


def get_solutions_for_target(framework: dict, dim: str, target_level: int) -> list[dict]:
    """Solutions mapped to this exact dimension+level, topped up (from the
    dimension's fallback list, then its other levels) to 3-5 items, since
    most levels only have 1-2 solutions mapped directly in the workbook."""
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
        out.append({"name": s["name"], "vp": vp, "portfolio": bank_entry.get("portfolio", "")})
    return out


# ===========================================================================
# RESULTS — TAB 1: Overview
# ===========================================================================
def render_radar(lang: str, answers: dict, framework: dict) -> None:
    """Pentagon spider chart: two outlined, dot-marker polygons — the MVS
    benchmark in red and the participant's current state in blue — matching
    the reference mockup's line-chart style (no filled wedges). Dimensions
    marked 0/not-assessed get a hollow gray marker on the current-state line
    instead of a colored dot, since the polygon itself must stay closed."""
    n = len(DIMENSIONS)
    centers = [i * 360 / n for i in range(n)]

    values = [answers[d] for d in DIMENSIONS]
    mvs_values = [framework[d]["mvs"] for d in DIMENSIONS]
    labels = [f"{DIMENSION_ICONS[d]}<br>{DIMENSION_NAMES[lang][d]}" for d in DIMENSIONS]
    not_assessed = [v == 0 for v in values]
    current_marker_colors = ["#B0B0B0" if na else PRIMARY for na in not_assessed]

    # Close each polygon by repeating the first point at the end.
    theta_closed = centers + [centers[0]]
    mvs_closed = mvs_values + [mvs_values[0]]
    values_closed = values + [values[0]]
    marker_colors_closed = current_marker_colors + [current_marker_colors[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=mvs_closed, theta=theta_closed, mode="lines+markers",
            line=dict(color=REFERENCE_RED, width=3),
            marker=dict(color=REFERENCE_RED, size=9),
            name=t(lang, "series_mvs"),
            customdata=[DIMENSION_NAMES[lang][d] for d in DIMENSIONS] + [DIMENSION_NAMES[lang][DIMENSIONS[0]]],
            hovertemplate="%{customdata} — " + t(lang, "series_mvs") + ": %{r}/5<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=values_closed, theta=theta_closed, mode="lines+markers",
            line=dict(color=PRIMARY, width=3),
            marker=dict(color=marker_colors_closed, size=9),
            name=t(lang, "series_current"),
            customdata=[DIMENSION_NAMES[lang][d] for d in DIMENSIONS] + [DIMENSION_NAMES[lang][DIMENSIONS[0]]],
            hovertemplate="%{customdata} — " + t(lang, "series_current") + ": %{r}/5<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                range=[0, 5], tickvals=[1, 2, 3, 4, 5], showticklabels=True,
                gridcolor=RADAR_TRACK_COLOR, linecolor=RADAR_TRACK_COLOR,
                tickfont=dict(size=11, color="#666666"),
            ),
            angularaxis=dict(
                tickmode="array", tickvals=centers, ticktext=labels,
                direction="clockwise", rotation=90, showgrid=True, gridcolor=RADAR_TRACK_COLOR,
                linecolor=RADAR_TRACK_COLOR, tickfont=dict(size=14, color=NAVY_TEXT),
            ),
            bgcolor="#FFFFFF",
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.1, x=0.2, font=dict(color=NAVY_TEXT)),
        margin=dict(l=80, r=80, t=50, b=50),
        height=480,
        paper_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True, config={"staticPlot": True})


def render_category_radar(lang: str, by_category: dict) -> None:
    """Same pentagon spider chart as render_radar, but with one outlined
    polygon per food category (in a fixed, colorblind-safe color order)
    instead of a single participant-vs-MVS pair — used on the live/audience
    aggregate view so each category's average maturity is visible at once."""
    n = len(DIMENSIONS)
    centers = [i * 360 / n for i in range(n)]
    labels = [f"{DIMENSION_ICONS[d]}<br>{DIMENSION_NAMES[lang][d]}" for d in DIMENSIONS]
    theta_closed = centers + [centers[0]]
    customdata = [DIMENSION_NAMES[lang][d] for d in DIMENSIONS] + [DIMENSION_NAMES[lang][DIMENSIONS[0]]]

    fig = go.Figure()

    for cat in FOOD_CATEGORIES:
        if cat not in by_category:
            continue
        cat_data = by_category[cat]
        values = [cat_data["averages"][d] for d in DIMENSIONS]
        values_closed = values + [values[0]]
        color = CATEGORY_COLORS[cat]
        cat_label = food_category_label(lang, cat)
        fig.add_trace(
            go.Scatterpolar(
                r=values_closed, theta=theta_closed, mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(color=color, size=9),
                name=f"{cat_label} (n={cat_data['count']})",
                customdata=customdata,
                hovertemplate="%{customdata} — " + cat_label + ": %{r}/5<extra></extra>",
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                range=[0, 5], tickvals=[1, 2, 3, 4, 5], showticklabels=True,
                gridcolor=RADAR_TRACK_COLOR, linecolor=RADAR_TRACK_COLOR,
                tickfont=dict(size=11, color="#666666"),
            ),
            angularaxis=dict(
                tickmode="array", tickvals=centers, ticktext=labels,
                direction="clockwise", rotation=90, showgrid=True, gridcolor=RADAR_TRACK_COLOR,
                linecolor=RADAR_TRACK_COLOR, tickfont=dict(size=14, color=NAVY_TEXT),
            ),
            bgcolor="#FFFFFF",
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center", font=dict(color=NAVY_TEXT)),
        margin=dict(l=80, r=80, t=50, b=50),
        height=520,
        paper_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True, config={"staticPlot": True})


def _savings_table_html(lang: str, answers: dict, framework: dict, food_category: str) -> str:
    savings = dl.savings_row_for_category(dl.load_workbook_data()["mvs_savings"], food_category)

    rows = []
    for kpi in ["oee", "quality", "energy", "stock"]:
        relevant = KPI_DIMENSIONS[kpi]
        assessed_relevant = [d for d in relevant if answers[d] > 0]
        if not assessed_relevant:
            value = t(lang, "not_assessed_kpi")
        elif all(answers[d] >= framework[d]["mvs"] for d in assessed_relevant):
            value = t(lang, "already_at_mvs")
        else:
            value = savings.get(kpi, "")
        rows.append(
            '<tr><td style="padding:8px 10px;border-bottom:1px solid #E5E5E5;">'
            f'<div style="font-weight:600;">{KPI_LABELS[lang][kpi]}</div>'
            f'<div style="color:#777;font-size:0.82rem;margin-top:2px;">{KPI_DESCRIPTIONS[lang][kpi]}</div>'
            "</td>"
            f'<td style="padding:8px 10px;border-bottom:1px solid #E5E5E5;font-weight:700;color:{PRIMARY};">{value}</td></tr>'
        )

    table = (
        '<table style="border-collapse:collapse;width:100%;font-size:0.94rem;">'
        '<thead><tr style="border-bottom:2px solid #ccc;">'
        f'<th style="text-align:left;padding:8px 10px;">{t(lang, "savings_kpi_col")}</th>'
        f'<th style="text-align:left;padding:8px 10px;">{t(lang, "savings_value_col")}</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )
    footnote = f'<p style="color:#888;font-size:0.78rem;margin-top:8px;">{t(lang, "savings_footnote")}</p>'
    return table + footnote


def render_overview_tab(lang: str, answers: dict, framework: dict, food_category: str) -> None:
    st.markdown(t(lang, "radar_title"))
    render_radar(lang, answers, framework)
    if any(v == 0 for v in answers.values()):
        st.caption(t(lang, "not_assessed_note"))
    st.info(f"**{t(lang, 'mvs_info_title')}** — {t(lang, 'mvs_info_body')}")

    st.divider()
    st.markdown(t(lang, "savings_title"))
    st.caption(t(lang, "savings_caption", category=food_category_label(lang, food_category)))
    st.markdown(_savings_table_html(lang, answers, framework, food_category), unsafe_allow_html=True)


# ===========================================================================
# RESULTS — TAB 2: Recommendations
# ===========================================================================
def render_recommendations_tab(lang: str, answers: dict, framework: dict) -> None:
    st.markdown(t(lang, "reco_title"))

    top = get_top_recommendations(answers)
    if not top:
        st.info(t(lang, "reco_need_assessment"))
        return

    for rec in top:
        dim = rec["dimension"]
        with st.container(border=True):
            st.markdown(f"#### {DIMENSION_ICONS[dim]} {DIMENSION_NAMES[lang][dim]}")

            if rec["mastered"]:
                st.markdown(f"**{t(lang, 'reco_mastered_title')}**")
                st.markdown(translate_fw(lang, framework[dim]["next_step"]))
                continue

            st.markdown(
                f'<span style="background:#EEF3FA;border:1px solid #DCE6F2;border-radius:8px;'
                f'padding:4px 10px;font-weight:700;color:{PRIMARY};">'
                f'{t(lang, "reco_level_transition", current=rec["current"], target=rec["target"])}</span>',
                unsafe_allow_html=True,
            )
            st.markdown("")

            def _level_card(label: str, lvl_num: int, bg: str, border: str, text_color: str) -> str:
                info = framework[dim]["levels"].get(lvl_num)
                if not info:
                    return ""
                name = translate_fw(lang, info["name"])
                desc = translate_fw(lang, info["description"])
                return (
                    f'<div style="flex:1 1 260px;background:{bg};border:2px solid {border};'
                    'border-radius:10px;padding:14px 18px;">'
                    f'<div style="color:{text_color};font-weight:800;font-size:1.02rem;margin-bottom:6px;">'
                    f"{label}: {lvl_num}</div>"
                    f'<div style="color:{text_color};font-weight:700;margin-bottom:4px;">{name}</div>'
                    f'<div style="color:{text_color};font-size:0.88rem;line-height:1.4;opacity:.9;">{desc}</div>'
                    "</div>"
                )

            st.markdown(
                '<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:10px 0 4px;">'
                + _level_card(t(lang, "reco_current_label"), rec["current"], PALE_BLUE, PRIMARY, NAVY_TEXT)
                + '<div style="flex:0 0 auto;font-size:1.6rem;color:#999;">→</div>'
                + _level_card(t(lang, "reco_target_label"), rec["target"], GREEN_BG, GREEN_BORDER, GREEN_TEXT)
                + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown("")

            solutions = get_solutions_for_target(framework, dim, rec["target"])
            if solutions:
                st.markdown(f"**{t(lang, 'reco_solutions_heading')}**")
            else:
                st.caption(t(lang, "solutions_none"))
            for s in solutions:
                st.markdown(
                    f'<div style="margin:6px 0;">'
                    f'<span style="margin-right:6px;">✅</span>'
                    f'<span style="font-weight:700;">{s["name"]}</span><br>'
                    f'<span style="color:#555;font-size:0.9rem;">{translate_fw(lang, s["vp"])}</span></div>',
                    unsafe_allow_html=True,
                )
        st.markdown("")


# ===========================================================================
# RESULTS — TAB 3: Customer stories
# ===========================================================================
def _pick_stories_for_dimension(
    all_stories: list[dict], dim: str, food_category: str, bucket: str, seen: set[str]
) -> list[dict]:
    """Candidates for one dimension, ranked by category/bucket match, skipping
    any customer already picked for a previous dimension (seen is shared
    across the whole tab so a story never repeats)."""
    candidates = [s for s in all_stories if s["dimension"] == dim and s["customer"] not in seen]
    if not candidates:
        return []

    def _score(s: dict) -> tuple:
        cat_match = s["food_category"].strip().lower() == food_category.strip().lower()
        bucket_match = s["maturity_bucket"] == bucket
        return (cat_match, bucket_match)

    ranked = sorted(candidates, key=_score, reverse=True)
    picked = []
    for s in ranked:
        if s["customer"] in seen:
            continue
        seen.add(s["customer"])
        picked.append(s)
        if len(picked) == 2:
            break
    return picked


def render_stories_tab(lang: str, answers: dict, food_category: str) -> None:
    st.markdown(t(lang, "stories_title"))

    top = get_top_recommendations(answers)
    if not top:
        st.info(t(lang, "reco_need_assessment"))
        return

    all_stories = dl.load_workbook_data()["customer_stories"]
    seen: set[str] = set()
    shown = 0
    for rec in top:
        if shown >= 6:
            break
        dim = rec["dimension"]
        bucket = "1-2" if rec["current"] <= 2 else ("3" if rec["current"] == 3 else "4-5")
        stories = _pick_stories_for_dimension(all_stories, dim, food_category, bucket, seen)
        for s in stories:
            if shown >= 6:
                break
            st.markdown(f'📄 [{s["customer"]}]({s["url"]})')
            shown += 1

    if shown == 0:
        st.caption(t(lang, "stories_none"))


# ===========================================================================
# RESULTS — assembly
# ===========================================================================
def render_results() -> None:
    lang = st.session_state["lang"]

    if st.session_state.pop("scroll_top", False):
        scroll_to_top()

    answers = st.session_state["answers"]
    profile = st.session_state["profile"]
    framework = dl.load_workbook_data()["framework"]

    st.markdown(f"## {t(lang, 'results_for', name=profile.get('name', ''), company=profile.get('company', ''))}")

    tab_overview, tab_reco, tab_stories = st.tabs(
        [t(lang, "tab_overview"), t(lang, "tab_reco"), t(lang, "tab_stories")]
    )
    with tab_overview:
        render_overview_tab(lang, answers, framework, profile.get("food_category", "Dairy"))
    with tab_reco:
        render_recommendations_tab(lang, answers, framework)
    with tab_stories:
        render_stories_tab(lang, answers, profile.get("food_category", "Dairy"))

    st.divider()
    food_category = profile.get("food_category", "Dairy")
    audience = _audience_aggregate_for_category(food_category)
    pdf_bytes = build_results_pdf(
        lang, profile, answers, framework, food_category,
        audience_averages=audience["averages"], audience_count=audience["count"],
    )
    st.download_button(
        t(lang, "download_pdf"),
        data=pdf_bytes,
        file_name=f"at-10000-feet-{profile.get('name', 'results').strip().replace(' ', '_').lower()}.pdf",
        mime="application/pdf",
        type="primary",
    )

    cols = st.columns([1, 1, 3])
    with cols[0]:
        if st.button(t(lang, "edit_answers")):
            st.session_state["dim_index"] = len(DIMENSIONS) - 1
            st.session_state["screen"] = "assessment"
            st.rerun()
    with cols[1]:
        if st.button(t(lang, "start_over")):
            keep_ws = st.session_state.get("gs_worksheet")
            st.session_state.clear()
            if keep_ws is not None:
                st.session_state["gs_worksheet"] = keep_ws
            st.rerun()


# ===========================================================================
# SCREEN — Live Results (organizer/projector view, via ?view=live)
# ===========================================================================
def render_live_results() -> None:
    lang = st.session_state["lang"]

    @st.fragment(run_every="10s")
    def _live_fragment():
        agg = _compute_live_aggregate()
        st.markdown(f"# {t(lang, 'live_title')}")

        if agg["count"] == 0:
            st.info(t(lang, "live_empty"))
            return

        st.caption(t(lang, "live_count", count=agg["count"]))
        render_category_radar(lang, agg["by_category"])

    _live_fragment()


# ===========================================================================
# APP ENTRY
# ===========================================================================
def main() -> None:
    st.set_page_config(
        page_title="At 10,000 Feet — Maturity Assessment",
        page_icon="🛫",
        layout="wide",
    )

    st.markdown(
        """
        <style>
          .stApp { background-color: #F5F5F5; }
          .block-container { padding-top: 2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    init_state()
    render_language_switcher()
    lang = st.session_state["lang"]

    if st.query_params.get("view") == "live":
        render_live_results()
        return

    if not _has_google_secrets():
        st.sidebar.warning(t(lang, "dev_warning", csv=LOCAL_CSV))

    screen = st.session_state["screen"]
    if screen == "welcome":
        render_welcome()
    elif screen == "profile":
        render_profile()
    elif screen == "motivation":
        render_motivation()
    elif screen == "assessment":
        render_assessment_step()
    else:
        render_results()


if __name__ == "__main__":
    main()
