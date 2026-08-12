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
from translations import (
    DIMENSION_ICONS,
    DIMENSION_NAMES,
    DIMENSION_PRIORITY,
    FALLBACK_SOLUTIONS,
    KPI_DIMENSIONS,
    KPI_LABELS,
    UI,
    t,
    translate_fw,
)

DIMENSIONS: list[str] = dl.DIMENSIONS  # ["strategy", "people", "operations", "connectivity", "intelligence"]

FOOD_CATEGORIES = ["Dairy", "Beverage", "Plant-based", "Cheese", "Powder", "Ice Cream", "Other"]


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
RADAR_TRACK_COLOR = "#E3E6EA"


# ===========================================================================
# ANALYTICS — persistence
# ===========================================================================
SHEET_HEADER = (
    ["timestamp_iso", "share_data", "name", "company", "email", "food_category", "motivation", "language"]
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
        [profile["name"], profile["company"], profile["email"], profile.get("food_category", ""), profile.get("motivation", "")]
        if share_data else ["", "", "", profile.get("food_category", ""), ""]
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


def _compute_live_aggregate() -> dict:
    """Average maturity level per dimension across every submission so far
    (0/not-assessed answers are excluded from each dimension's average)."""
    rows = _fetch_all_submissions()
    count = len(rows)
    if count == 0:
        return {"count": 0, "averages": {d: 0.0 for d in DIMENSIONS}}

    averages = {}
    for dim in DIMENSIONS:
        col = f"{dim}_level"
        values = [float(r[col]) for r in rows if str(r.get(col, "")).strip() not in ("", "0")]
        averages[dim] = round(sum(values) / len(values), 1) if values else 0.0
    return {"count": count, "averages": averages}


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
    st.subheader(f"{t(lang, 'motivation_question')} {t(lang, 'motivation_optional')}")

    current = st.session_state["profile"].get("motivation", "")
    answer = st.text_area(
        t(lang, "motivation_question"),
        value=current,
        placeholder=t(lang, "motivation_placeholder"),
        key="in_motivation",
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
            st.session_state["profile"]["motivation"] = answer.strip()
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
    for lvl_num in sorted(levels_with_zero.keys()):
        level_info = levels_with_zero[lvl_num]
        name = translate_fw(lang, level_info["name"])
        desc = translate_fw(lang, level_info["description"])
        is_selected = lvl_num == current_answer
        if st.button(
            _level_option_label(lvl_num, name, desc),
            key=f"opt_{dim}_{lvl_num}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state["answers"][dim] = lvl_num
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
    """Step A: solutions mapped to this exact dimension+level. Step B
    (fallback): dimension-wide fallback list if that level has none."""
    solutions_bank = dl.load_workbook_data()["solutions_bank"]
    sols = framework[dim]["solutions"].get(target_level, [])
    if not sols:
        sols = [{"name": name, "vp": None} for name in FALLBACK_SOLUTIONS.get(dim, [])]

    out = []
    for s in sols:
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
    st.plotly_chart(fig, use_container_width=True)


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
            f'<tr><td style="padding:8px 10px;border-bottom:1px solid #E5E5E5;">{KPI_LABELS[lang][kpi]}</td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #E5E5E5;font-weight:700;color:{PRIMARY};">{value}</td></tr>'
        )

    return (
        '<table style="border-collapse:collapse;width:100%;font-size:0.94rem;">'
        '<thead><tr style="border-bottom:2px solid #ccc;">'
        f'<th style="text-align:left;padding:8px 10px;">{t(lang, "savings_kpi_col")}</th>'
        f'<th style="text-align:left;padding:8px 10px;">{t(lang, "savings_value_col")}</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def render_overview_tab(lang: str, answers: dict, framework: dict, food_category: str) -> None:
    st.markdown(t(lang, "radar_title"))
    render_radar(lang, answers, framework)
    if any(v == 0 for v in answers.values()):
        st.caption(t(lang, "not_assessed_note"))
    st.info(f"**{t(lang, 'mvs_info_title')}** — {t(lang, 'mvs_info_body')}")

    st.divider()
    st.markdown(t(lang, "savings_title"))
    st.caption(t(lang, "savings_caption", category=food_category))
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

            solutions = get_solutions_for_target(framework, dim, rec["target"])
            if not solutions:
                st.caption(t(lang, "solutions_none"))
            for s in solutions:
                badge = (
                    f'<span style="background:{PALE_BLUE};color:{NAVY_TEXT};border-radius:8px;'
                    f'padding:2px 8px;font-size:0.72rem;font-weight:700;margin-left:8px;">{t(lang, "factory_os_badge")}</span>'
                    if s["portfolio"] == "Factory OS" else ""
                )
                st.markdown(
                    f'<div style="margin:6px 0;">'
                    f'<span style="margin-right:6px;">✅</span>'
                    f'<span style="font-weight:700;">{s["name"]}</span>{badge}<br>'
                    f'<span style="color:#555;font-size:0.9rem;">{translate_fw(lang, s["vp"])}</span></div>',
                    unsafe_allow_html=True,
                )
        st.markdown("")


# ===========================================================================
# RESULTS — TAB 3: Customer stories
# ===========================================================================
def _pick_stories_for_dimension(all_stories: list[dict], dim: str, food_category: str, bucket: str) -> list[dict]:
    candidates = [s for s in all_stories if s["dimension"] == dim]
    if not candidates:
        return []

    def _score(s: dict) -> tuple:
        cat_match = s["food_category"].strip().lower() == food_category.strip().lower()
        bucket_match = s["maturity_bucket"] == bucket
        return (cat_match, bucket_match)

    ranked = sorted(candidates, key=_score, reverse=True)
    seen = set()
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
    shown = 0
    any_story = False
    for rec in top:
        if shown >= 6:
            break
        dim = rec["dimension"]
        bucket = "1-2" if rec["current"] <= 2 else ("3" if rec["current"] == 3 else "4-5")
        stories = _pick_stories_for_dimension(all_stories, dim, food_category, bucket)
        for s in stories:
            if shown >= 6:
                break
            any_story = True
            st.markdown(t(lang, "stories_context", dimension=DIMENSION_NAMES[lang][dim]))
            st.markdown(
                f'<div style="background:#F7F9FC;border:1px solid #DCE6F2;border-radius:10px;'
                f'padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-weight:700;font-size:1.0rem;">{s["customer"]}</div>'
                f'<a href="{s["url"]}" target="_blank">{t(lang, "read_story")}</a>'
                f'</div>',
                unsafe_allow_html=True,
            )
            shown += 1

    if not any_story:
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
        framework = dl.load_workbook_data()["framework"]
        synthetic_answers = {d: agg["averages"][d] for d in DIMENSIONS}
        render_radar(lang, synthetic_answers, framework)

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
