"""
At 10,000 Feet — Intelligent Automation Maturity Assessment
============================================================
Single-file Streamlit app for Foro MX 2026.

Screens (st.session_state["screen"]): "welcome" | "questions" | "results".

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

# ===========================================================================
# 4. DATA — Questions
# ===========================================================================
QUESTIONS: dict[str, list[str]] = {
    "Data": [
        "My operating systems (ERP, MES, PLC) share data in real time or are fully integrated.",
        "I trust the quality of my operational data (it is accurate, complete, consistent).",
        "There is clear governance: I know who owns each piece of data, who can access it, and how it's used.",
        "I can access historical and contextualized data for analysis and projections.",
    ],
    "Infrastructure": [
        "My production equipment (machines, sensors, lines) is connected and automatically sends digital data.",
        "I can share data between different systems without manual intervention (interoperability).",
        "I have defined and implemented cybersecurity protocols (controlled access, encryption, auditing).",
        "My infrastructure (networks, servers, cloud) is designed to support real-time analysis and future growth.",
    ],
    "Investment & Prioritization": [
        "I have clarity on the top 3-5 operational challenges to solve in the next 2-3 years.",
        "For each automation/digitalization initiative, I have built a documented business case (ROI, timeline, resources).",
        "I have approved budget and financing mechanisms (capex, opex, partner financing) to move forward.",
        "My leadership has communicated that digital transformation/automation is a strategic priority.",
    ],
    "Change Management": [
        "I have defined training/upskilling plans so my team can use new tools and data.",
        "There is a visible and committed executive sponsor leading the transformation.",
        "My operational team sees change as an opportunity (not a threat to their jobs).",
        "I have people in my organization with skills in data, analytics, and Industry 4.0 (or plans to acquire them).",
    ],
    "Operational Control & CI": [
        "My operational processes are predictable, repeatable, and well documented (I know exactly what happens at each step).",
        "We have a culture and structure of continuous improvement: we measure, analyze, and optimize regularly (not ad-hoc).",
    ],
}

# Icon per pillar — reused in the results list and on the radar vertices.
PILLAR_ICONS: dict[str, str] = {
    "Data": "🗄️",
    "Infrastructure": "🏗️",
    "Investment & Prioritization": "💰",
    "Change Management": "🔄",
    "Operational Control & CI": "⚙️",
}

# Short one-line summaries used on the welcome screen.
PILLAR_BLURBS: dict[str, str] = {
    "Data": "Quality, governance and access to your operational data.",
    "Infrastructure": "Connectivity, interoperability, cybersecurity and scalability.",
    "Investment & Prioritization": "Clear priorities, business cases and funded roadmap.",
    "Change Management": "Sponsorship, training, culture and talent.",
    "Operational Control & CI": "Process discipline and continuous improvement.",
}

# Column-name stems for the analytics sheet, matching pillar order.
PILLAR_KEYS: dict[str, str] = {
    "Data": "data",
    "Infrastructure": "infra",
    "Investment & Prioritization": "invest",
    "Change Management": "change",
    "Operational Control & CI": "opctrl",
}

# ===========================================================================
# 6. LEVELS (global)
# ===========================================================================
LEVELS = [
    {"min": 0, "max": 8, "num": 0, "name": "INACTIVE",
     "description": "Isolated systems, unreliable data, legacy infrastructure, no clear budget or training. Ad-hoc processes with no continuous improvement: you are not ready for digital transformation."},
    {"min": 9, "max": 17, "num": 1, "name": "REACTIVE",
     "description": "Partial data and infrastructure, reactive investment with no business case, resistant team. You're moving slowly without a clear strategy: you need a roadmap and a dedicated team."},
    {"min": 18, "max": 26, "num": 2, "name": "ACTIVE",
     "description": "Integrated systems, clear priorities, approved budget, team in transition, documented processes. You're on the path: modernize infrastructure and raise data governance."},
    {"min": 27, "max": 36, "num": 3, "name": "ESTABLISHED",
     "description": "Reliable data, integrated infrastructure, roadmap with clear financing, trained team, stable operations. You're ready for AI: you can invest in automation with confidence."},
    {"min": 37, "max": 45, "num": 4, "name": "INTEGRATED",
     "description": "Strategic data, modern infrastructure, monitored investment, talent center of excellence, data-driven improvement. You're a benchmark: your focus is continuous innovation."},
    {"min": 46, "max": 54, "num": 5, "name": "PROACTIVE",
     "description": "Mature data ecosystem, zero-trust infrastructure, reinvestment-based financing, learning-first talent, integrated AI. You're an industry leader: you lead ecosystem transformation."},
]

# ===========================================================================
# 7. RECOMMENDATIONS catalog (keys must exactly match QUESTIONS.keys())
# ===========================================================================
RECOMMENDATIONS: dict[str, list[dict]] = {
    "Data": [
        {"transition": "0→1", "title": "Consolidate data in pilot data lake",
         "description": "Integrate data from 2-3 operational systems (ERP, MES, production) into a centralized basic repository for initial analysis.",
         "factory_os": "no"},
        {"transition": "1→2", "title": "Document data governance framework",
         "description": "Define in writing: who owns each key data asset, who accesses it, minimum quality standards, retention policies, data lineage.",
         "factory_os": "no"},
        {"transition": "2→3", "title": "Implement Master Data Management (MDM)",
         "description": "Create single source of truth for master data: products, locations, equipment, suppliers. Eliminate duplicates and conflicts.",
         "factory_os": "no"},
        {"transition": "3→4", "title": "Deploy data catalog with automated lineage",
         "description": "Tool that maps origin, transformations, and usage of each data asset. Include automated quality monitoring.",
         "factory_os": "no"},
        {"transition": "4→5", "title": "Implement predictive ML models",
         "description": "Develop models for demand forecasting, predictive maintenance, inventory optimization using historical data.",
         "factory_os": "yes"},
    ],
    "Infrastructure": [
        {"transition": "0→1", "title": "Cybersecurity audit + patch critical systems",
         "description": "Assess vulnerabilities in legacy machines, apply critical patches, identify disconnected equipment, document gaps.",
         "factory_os": "no"},
        {"transition": "1→2", "title": "Connect equipment with IoT sensors / adapters",
         "description": "Install sensors or gateways on key machines to send production data automatically (no manual intervention).",
         "factory_os": "yes"},
        {"transition": "2→3", "title": "Implement security-by-design architecture",
         "description": "Segregate OT/IT networks, implement VPN, multi-factor authentication, encryption in transit, access audit trails.",
         "factory_os": "partially"},
        {"transition": "3→4", "title": "Migrate to hybrid cloud or edge computing",
         "description": "Move certain data and processing to cloud (with on-premise for sensitive data). Enable real-time processing near equipment.",
         "factory_os": "yes"},
        {"transition": "4→5", "title": "Implement zero-trust architecture",
         "description": "Micro-segmentation, continuous monitoring, automated threat response, assume breach always present.",
         "factory_os": "yes"},
    ],
    "Investment & Prioritization": [
        {"transition": "0→1", "title": "Map top 5 operational challenges with impact",
         "description": "Create 2x2 matrix: urgency vs. financial impact. Quantify current losses per challenge.",
         "factory_os": "no"},
        {"transition": "1→2", "title": "Develop 3 formal business cases",
         "description": "For each top initiative: investment, expected ROI (%), timeline, assumptions, identified risks, responsible team.",
         "factory_os": "no"},
        {"transition": "2→3", "title": "Create investment governance (steering committee)",
         "description": "Quarterly committee that prioritizes projects, allocates budget, reviews progress vs. plan. Use scoring matrix (ROI × Strategic fit × Risk).",
         "factory_os": "no"},
        {"transition": "3→4", "title": "Implement financial tracking dashboard",
         "description": "Real-time dashboard: actual vs. budgeted investment, cumulative ROI vs. projected, variances, automatic rebalancing.",
         "factory_os": "yes"},
        {"transition": "4→5", "title": "Establish open innovation model",
         "description": "Set aside 10-15% of budget for pilots, partnerships with startups/universities, internal venture arm.",
         "factory_os": "partially"},
    ],
    "Change Management": [
        {"transition": "0→1", "title": "Appoint executive sponsor and core team",
         "description": "Name a visible C-level leader (sponsor), dedicate a core team of 3-5 people full-time to lead transformation.",
         "factory_os": "no"},
        {"transition": "1→2", "title": "Launch structured communication plan",
         "description": "Key messages, 3-4 channels (town halls, newsletters, floor), weekly/monthly cadence, storytelling with tangible early wins.",
         "factory_os": "no"},
        {"transition": "2→3", "title": "Design role-based training program",
         "description": "Identify 5 critical roles, specific modules per role (data analysts, operators, supervisors), hands-on labs, internal certification.",
         "factory_os": "no"},
        {"transition": "3→4", "title": "Create center of excellence",
         "description": "Dedicated team of 5-8 people in data, analytics, automation. Coach/mentor roles. Monthly internal community (show & tell).",
         "factory_os": "no"},
        {"transition": "4→5", "title": "Transform into learning organization",
         "description": "Annual budget per person for training, conferences, certifications. Publish case studies or research papers. Retain senior talent as mentors.",
         "factory_os": "no"},
    ],
    "Operational Control & CI": [
        {"transition": "0→1", "title": "Document 5 critical operational processes",
         "description": "Map as-is: flows, owners, cycle times, associated KPIs. Use SIPOC diagrams or value stream mapping.",
         "factory_os": "no"},
        {"transition": "1→2", "title": "Implement visual control on floor",
         "description": "Line dashboards with real-time KPIs, daily control board, 10-15 min huddles with data review. Full visibility.",
         "factory_os": "yes"},
        {"transition": "2→3", "title": "Structure continuous improvement cycle (PDCA)",
         "description": "Monthly kaizen team, Plan-Do-Check-Act methodology, public idea tracking (submitted vs. implemented), goal: 1 improvement per person / year.",
         "factory_os": "no"},
        {"transition": "3→4", "title": "Implement data-driven automatic optimization",
         "description": "Algorithms that suggest improvements: setup changes, line speed, product mix. Automatic recommendations on dashboard.",
         "factory_os": "yes"},
        {"transition": "4→5", "title": "Automate operational decisions with AI",
         "description": "System that adjusts in real-time: line speed, product mix, predictive maintenance, without human intervention (within parameters).",
         "factory_os": "yes"},
    ],
}

# ===========================================================================
# 9. STYLE constants
# ===========================================================================
PRIMARY = "#7B9BC9"
CAPSULE_FILL = "#B8CCE4"
ACCENT = "#7B9BC9"

PILLARS = list(QUESTIONS.keys())  # canonical radar / display order


# ===========================================================================
# 5. SCORING LOGIC
# ===========================================================================
def pillar_max(pillar: str) -> int:
    """Max score for a pillar = number of questions * 3."""
    return len(QUESTIONS[pillar]) * 3


def get_pillar_level(raw: int, pmax: int) -> int:
    """Map a pillar's raw score to a 0-5 level using proportional cuts
    consistent with the global LEVELS table."""
    pct = raw / pmax * 100
    if pct <= 15:
        return 0   # Inactive
    if pct <= 31:
        return 1   # Reactive
    if pct <= 48:
        return 2   # Active
    if pct <= 66:
        return 3   # Established
    if pct <= 84:
        return 4   # Integrated
    return 5       # Proactive


def level_for_total(total: int) -> dict:
    """Return the LEVELS entry whose [min, max] contains total."""
    for lvl in LEVELS:
        if lvl["min"] <= total <= lvl["max"]:
            return lvl
    return LEVELS[-1]


def level_name(num: int) -> str:
    """Level name for a 0-5 level number."""
    return LEVELS[num]["name"]


# ===========================================================================
# 8. ANALYTICS — persistence
# ===========================================================================
SHEET_HEADER = (
    ["timestamp_iso", "name", "company", "email", "role"]
    + [f"q_{PILLAR_KEYS[p]}_{i + 1}" for p in PILLARS for i in range(len(QUESTIONS[p]))]
    + [f"{PILLAR_KEYS[p]}_raw" for p in PILLARS]
    + [f"{PILLAR_KEYS[p]}_level" for p in PILLARS]
    + ["total", "level_num", "level_name"]
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

        # Create header row if the worksheet is empty.
        if not ws.get_all_values():
            ws.append_row(SHEET_HEADER, value_input_option="RAW")

        st.session_state["gs_worksheet"] = ws
        return ws
    except Exception as exc:  # noqa: BLE001
        print(f"[analytics] Google Sheets auth failed: {exc}")
        st.session_state["gs_worksheet"] = None
        return None


def build_row(profile: dict, answers: dict) -> list:
    """Assemble one analytics row in the fixed column order."""
    flat_answers = [answers[p][i] for p in PILLARS for i in range(len(QUESTIONS[p]))]
    raws = [sum(answers[p]) for p in PILLARS]
    levels = [get_pillar_level(sum(answers[p]), pillar_max(p)) for p in PILLARS]
    total = sum(raws)
    lvl = level_for_total(total)
    return (
        [
            datetime.now(timezone.utc).isoformat(),
            profile["name"], profile["company"], profile["email"], profile["role"],
        ]
        + flat_answers
        + raws
        + levels
        + [total, lvl["num"], lvl["name"]]
    )


def persist_submission(profile: dict, answers: dict) -> None:
    """Append one row to Google Sheets, or fall back to local CSV.

    Never raises — analytics must not block the user from their result.
    """
    row = build_row(profile, answers)

    ws = _get_worksheet()
    if ws is not None:
        try:
            ws.append_row(row, value_input_option="RAW")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[analytics] append to Google Sheets failed: {exc}")

    # Local-dev fallback.
    try:
        write_header = not os.path.exists(LOCAL_CSV)
        with open(LOCAL_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(SHEET_HEADER)
            writer.writerow(row)
    except Exception as exc:  # noqa: BLE001
        print(f"[analytics] local CSV fallback failed: {exc}")


# ===========================================================================
# SESSION STATE INIT
# ===========================================================================
def init_state() -> None:
    st.session_state.setdefault("screen", "welcome")
    st.session_state.setdefault("profile", {})
    # answers[pillar] = list of len(questions) entries, each None or 0-3.
    if "answers" not in st.session_state:
        st.session_state["answers"] = {
            p: [None] * len(QUESTIONS[p]) for p in PILLARS
        }


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def scroll_to_top() -> None:
    """Scroll the parent page to the top.

    Streamlit keeps the scroll position across reruns, so after a screen change
    (notably on mobile) the user can land at the bottom of the new page. This
    injects a tiny script into the app iframe that scrolls its parent window.
    """
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


# ===========================================================================
# SCREEN 1 — Welcome + participant info
# ===========================================================================
def render_welcome() -> None:
    st.title("At 10,000 Feet: How Ready Are You for Intelligent Transition?")

    st.markdown(
        "This self-diagnostic helps you understand how prepared your operation is "
        "for **intelligent automation**. In a few minutes you'll answer 18 questions "
        "across five maturity pillars and receive a normalized profile, your overall "
        "readiness level, and a personalized roadmap of next moves."
    )
    st.markdown(
        "The five pillars are: "
        "**Data** (quality, governance, access) · "
        "**Infrastructure** (connectivity, security, scalability) · "
        "**Investment & Prioritization** (priorities, business cases, funding) · "
        "**Change Management** (sponsorship, training, culture) · "
        "**Operational Control & CI** (process discipline and continuous improvement)."
    )

    st.markdown(
        '<div style="font-size:1.5rem;font-weight:600;color:#333;margin:6px 0;">'
        '<span style="font-size:2.0rem;">✍️</span> Answer'
        ' &nbsp;→&nbsp; '
        '<span style="font-size:2.0rem;">🧮</span> Calculate'
        ' &nbsp;→&nbsp; '
        '<span style="font-size:2.0rem;">📊</span> Review'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.subheader("Tell us about you")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full name *", key="in_name")
        email = st.text_input("Work email *", key="in_email")
    with col2:
        company = st.text_input("Company *", key="in_company")
        role = st.text_input("Role / title *", key="in_role")

    consent = st.checkbox(
        "I agree that my anonymized responses may be used for Foro MX 2026 analytics.",
        key="in_consent",
    )

    email_ok = bool(EMAIL_RE.match(email.strip())) if email else False
    if email and not email_ok:
        st.caption(":red[Please enter a valid email address.]")

    all_filled = all(v.strip() for v in (name, company, email, role))
    can_start = all_filled and email_ok and consent

    if st.button("Start Assessment", type="primary", disabled=not can_start):
        st.session_state["profile"] = {
            "name": name.strip(),
            "company": company.strip(),
            "email": email.strip(),
            "role": role.strip(),
        }
        st.session_state["screen"] = "questions"
        st.rerun()


# ===========================================================================
# SCREEN 2 — Questionnaire
# ===========================================================================
def _count_answered() -> int:
    return sum(
        1
        for p in PILLARS
        for v in st.session_state["answers"][p]
        if v is not None
    )


def render_questions() -> None:
    total_q = sum(len(v) for v in QUESTIONS.values())
    answered = _count_answered()

    # Sticky progress indicator.
    st.markdown(f"### Answered {answered} of {total_q} questions")
    st.progress(answered / total_q)

    st.info(
        "**Scale:**  "
        "**0** — Not implemented / not present  ·  "
        "**1** — Early / partial  ·  "
        "**2** — Mostly in place  ·  "
        "**3** — Fully consolidated"
    )

    for idx, pillar in enumerate(PILLARS):
        p_answered = sum(1 for v in st.session_state["answers"][pillar] if v is not None)
        p_total = len(QUESTIONS[pillar])
        label = f"{PILLAR_ICONS[pillar]}  {pillar}  —  {p_answered}/{p_total} answered"
        # `expanded` is re-applied on every rerun, so a static False would slam
        # the section shut each time the user clicks a radio inside it. Keep a
        # pillar open once it's the first one or has any answer.
        keep_open = (idx == 0) or (p_answered > 0)
        with st.expander(label, expanded=keep_open):
            for qi, question in enumerate(QUESTIONS[pillar]):
                current = st.session_state["answers"][pillar][qi]
                choice = st.radio(
                    f"{question}",
                    options=[0, 1, 2, 3],
                    index=None if current is None else current,
                    horizontal=True,
                    key=f"q_{PILLAR_KEYS[pillar]}_{qi}",
                )
                st.session_state["answers"][pillar][qi] = choice

    st.divider()
    # Re-count after widgets may have updated state this run.
    answered = _count_answered()
    can_calc = answered == total_q

    cols = st.columns([1, 3])
    with cols[0]:
        if st.button("← Back", key="back_to_welcome"):
            st.session_state["screen"] = "welcome"
            st.rerun()
    with cols[1]:
        if st.button("Calculate My Score", type="primary", disabled=not can_calc):
            persist_submission(st.session_state["profile"], st.session_state["answers"])
            st.session_state["screen"] = "results"
            st.session_state["scroll_top"] = True
            st.rerun()

    if not can_calc:
        st.caption(f":grey[Answer all {total_q} questions to calculate your score.]")


# ===========================================================================
# SCREEN 3 — Results
# ===========================================================================
def _score_item_html(icon: str, big: str, small: str, name: str, *, total: bool) -> str:
    """One list item: icon + large number + small `/max` + small category name.

    Emitted as a single line with no leading indentation — Streamlit's markdown
    renderer treats 4-space-indented lines as a code block and would print the
    raw HTML as text.
    """
    fill = "#EEF3FA" if total else "#FFFFFF"
    border = f"2px solid {ACCENT}" if total else "1px solid #E0E6EF"
    num_size = "2.4rem" if total else "2.0rem"
    icon_size = "3.0rem" if total else "2.7rem"
    return (
        f'<div style="flex:1;min-width:150px;background:{fill};border:{border};'
        f'border-radius:12px;padding:14px 16px;box-shadow:0 2px 6px rgba(123,155,201,0.15);'
        f'display:flex;align-items:center;gap:14px;">'
        f'<div style="font-size:{icon_size};line-height:1;">{icon}</div>'
        f'<div style="display:flex;flex-direction:column;">'
        f'<div style="line-height:1.05;">'
        f'<span style="font-size:{num_size};font-weight:800;color:#1A1A1A;">{big}</span>'
        f'<span style="font-size:1.0rem;font-weight:600;color:#7688a0;">{small}</span>'
        f'</div>'
        f'<div style="font-size:0.8rem;color:#556;font-weight:600;margin-top:2px;">{name}</div>'
        f'</div></div>'
    )


def render_equation_block(answers: dict, total: int, lvl: dict) -> None:
    raws = {p: sum(answers[p]) for p in PILLARS}

    items = [
        _score_item_html(
            "🛫", f"{total}", "/54", f"YOUR READINESS — {lvl['name']}", total=True
        )
    ]
    for pillar in PILLARS:
        pmax = pillar_max(pillar)
        items.append(
            _score_item_html(
                PILLAR_ICONS[pillar], f"{raws[pillar]}", f"/{pmax}", pillar, total=False
            )
        )

    html = (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;padding:8px 0;">'
        + "".join(items)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_radar(answers: dict) -> None:
    pcts = [sum(answers[p]) / pillar_max(p) * 100 for p in PILLARS]
    # Short vertex labels, each carrying its pillar icon.
    short = ["Data", "Infrastructure", "Investment &<br>Prioritization",
             "Change<br>Management", "Operational<br>Control & CI"]
    labels = [f"{PILLAR_ICONS[p]}<br>{s}" for p, s in zip(PILLARS, short)]

    # Close the polygon.
    r = pcts + [pcts[0]]
    theta = labels + [labels[0]]
    text = [f"{v:.0f}%" for v in pcts] + [f"{pcts[0]:.0f}%"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r,
            theta=theta,
            fill="toself",
            fillcolor="rgba(123,155,201,0.5)",
            line=dict(color=PRIMARY, width=2),
            mode="lines+markers+text",
            text=text,
            textposition="top center",
            textfont=dict(size=13, color="#33455e"),
            hovertemplate="%{theta}: %{r:.0f}%<extra></extra>",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100],
                ticksuffix="%",
                gridcolor="#D7DEE9",
            ),
            angularaxis=dict(
                gridcolor="#D7DEE9",
                tickfont=dict(size=17, color="#333"),
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        margin=dict(l=80, r=80, t=50, b=50),
        height=460,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_level_table(lvl: dict) -> None:
    rows = []
    for L in LEVELS:
        achieved = L["num"] == lvl["num"]
        pts = f"{L['min']}–{L['max']}"
        if achieved:
            rows.append(
                f'<tr style="background:{CAPSULE_FILL};font-weight:700;">'
                f'<td style="padding:6px 10px;">{pts}</td>'
                f'<td style="padding:6px 10px;">L{L["num"]}</td>'
                f'<td style="padding:6px 10px;">{L["name"]}</td></tr>'
            )
        else:
            rows.append(
                f'<tr><td style="padding:6px 10px;color:#555;">{pts}</td>'
                f'<td style="padding:6px 10px;color:#555;">L{L["num"]}</td>'
                f'<td style="padding:6px 10px;color:#555;">{L["name"]}</td></tr>'
            )
    table = (
        '<table style="border-collapse:collapse;width:100%;font-size:0.92rem;">'
        '<thead><tr style="border-bottom:2px solid #ccc;">'
        '<th style="text-align:left;padding:6px 10px;">Points</th>'
        '<th style="text-align:left;padding:6px 10px;">Level</th>'
        '<th style="text-align:left;padding:6px 10px;">Level Name</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )
    st.markdown(table, unsafe_allow_html=True)


def render_overview_tab(answers: dict, total: int, lvl: dict) -> None:
    st.markdown("#### Your readiness equation")
    render_equation_block(answers, total, lvl)
    st.divider()

    st.markdown("#### A snapshot of your maturity level")
    render_radar(answers)
    st.divider()

    st.markdown("#### Your level")
    c1, c2 = st.columns([1, 1.3])
    with c1:
        render_level_table(lvl)
    with c2:
        st.markdown(
            f'<div style="font-size:1.15rem;font-weight:700;color:{PRIMARY};">'
            f'Level {lvl["num"]} — {lvl["name"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:1.02rem;line-height:1.5;color:#333;margin-top:8px;">'
            f'{lvl["description"]}</div>',
            unsafe_allow_html=True,
        )


def _stepper_step_html(step: dict, state: str) -> str:
    """Render one stepper step. state in {achieved, next, future}."""
    if state == "achieved":
        bg, border, icon, title_color, desc_color = "#E8F5E9", "none", "✅", "#666", "#666"
    elif state == "next":
        bg, border, icon, title_color, desc_color = "#EEF3FA", "2px solid #7B9BC9", "▶️", "#1A1A1A", "#333"
    else:  # future
        bg, border, icon, title_color, desc_color = "#F0F0F0", "none", "○", "#999", "#999"

    label = f"L{step['transition'].replace('→', ' → L')}"  # e.g. "L2 → L3"
    weight = "700" if state == "next" else "600"
    # Single line, no leading indentation (see _score_item_html for why).
    return (
        f'<div style="display:flex;gap:12px;background:{bg};border:{border};'
        f'border-radius:10px;padding:12px 14px;margin-bottom:8px;">'
        f'<div style="min-width:70px;display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;">'
        f'<div style="font-size:1.9rem;">{icon}</div>'
        f'<div style="font-size:0.78rem;color:{desc_color};font-weight:600;">{label}</div>'
        f'</div>'
        f'<div style="flex:1;">'
        f'<div style="font-weight:{weight};color:{title_color};font-size:1.0rem;">{step["title"]}</div>'
        f'<div style="color:{desc_color};font-size:0.9rem;line-height:1.4;margin-top:3px;">{step["description"]}</div>'
        f'</div></div>'
    )


def render_recommendations_tab(answers: dict) -> None:
    st.markdown(
        "Based on your scores, here's the maturity ladder for each pillar. "
        "✅ Achieved  ·  ▶️ Your next move  ·  ○ Future targets."
    )

    # Track FactoryOS acceleration data while rendering ladders.
    forward_total = 0
    accelerated: dict[str, list[dict]] = {}

    for pillar in PILLARS:
        raw = sum(answers[pillar])
        p_level = get_pillar_level(raw, pillar_max(pillar))
        steps = RECOMMENDATIONS[pillar]

        st.markdown(f"### {pillar} — Level {p_level} ({level_name(p_level)})")

        if p_level == 5:
            st.markdown(
                ':green[**You\'ve mastered this pillar. Focus on sustaining excellence.**]'
            )

        html_steps = []
        for step_index, step in enumerate(steps):
            if step_index < p_level:
                state = "achieved"
            elif step_index == p_level:
                state = "next"
            else:
                state = "future"
            html_steps.append(_stepper_step_html(step, state))

            # FactoryOS forward-journey accounting.
            if step_index >= p_level:
                forward_total += 1
                if step["factory_os"] in ("yes", "partially"):
                    accelerated.setdefault(pillar, []).append(step)

        st.markdown("".join(html_steps), unsafe_allow_html=True)
        st.markdown("")  # spacing

    # ------ FactoryOS accelerator box ------
    st.divider()
    accel_count = sum(len(v) for v in accelerated.values())

    box = [
        f'<div style="background:#F7F9FC;border:1px solid #DCE6F2;border-radius:14px;'
        f'padding:22px 26px;">',
        f'<div style="font-size:1.35rem;font-weight:800;color:{PRIMARY};margin-bottom:6px;">'
        f'How FactoryOS accelerates you</div>',
        f'<div style="font-size:1.02rem;color:#333;margin-bottom:14px;">'
        f'<b>{accel_count}</b> of your <b>{forward_total}</b> remaining recommended '
        f'actions can be accelerated with FactoryOS.</div>',
    ]

    for pillar in PILLARS:
        if pillar not in accelerated:
            continue
        box.append(
            f'<div style="font-weight:700;color:#1A1A1A;margin:10px 0 4px;">{pillar}</div>'
        )
        for step in accelerated[pillar]:
            if step["factory_os"] == "yes":
                badge = ('<span style="background:#E8F5E9;color:#2E7D32;border-radius:8px;'
                         'padding:2px 8px;font-size:0.72rem;font-weight:700;margin-left:8px;">Full</span>')
            else:
                badge = ('<span style="background:#FFF3E0;color:#E65100;border-radius:8px;'
                         'padding:2px 8px;font-size:0.72rem;font-weight:700;margin-left:8px;">Partial</span>')
            box.append(
                f'<div style="color:#333;font-size:0.94rem;margin:2px 0 2px 8px;">'
                f'• {step["title"]}{badge}</div>'
            )

    box.append('</div>')
    st.markdown("".join(box), unsafe_allow_html=True)

    st.markdown("")
    st.link_button("Learn more about FactoryOS →", "#", type="primary")


def render_results() -> None:
    # Jump to the top once, right after arriving from the questionnaire.
    if st.session_state.pop("scroll_top", False):
        scroll_to_top()

    answers = st.session_state["answers"]
    profile = st.session_state["profile"]
    total = sum(sum(answers[p]) for p in PILLARS)
    lvl = level_for_total(total)

    st.markdown(f"## Results for {profile.get('name', '')} — {profile.get('company', '')}")

    tab_overview, tab_reco = st.tabs(["Overview", "Recommendations"])
    with tab_overview:
        render_overview_tab(answers, total, lvl)
    with tab_reco:
        render_recommendations_tab(answers)

    st.divider()
    if st.button("Start Over"):
        keep_ws = st.session_state.get("gs_worksheet")
        st.session_state.clear()
        if keep_ws is not None:
            st.session_state["gs_worksheet"] = keep_ws
        st.rerun()


# ===========================================================================
# APP ENTRY
# ===========================================================================
def main() -> None:
    st.set_page_config(
        page_title="At 10,000 Feet — Maturity Assessment",
        page_icon="🛫",
        layout="wide",
    )

    # Light background + text color tweaks.
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

    # Dev-only warning when Google Sheets isn't configured.
    if not _has_google_secrets():
        st.sidebar.warning(
            "⚠️ Dev mode: Google Sheets not configured. "
            f"Submissions are being written to `{LOCAL_CSV}`."
        )

    screen = st.session_state["screen"]
    if screen == "welcome":
        render_welcome()
    elif screen == "questions":
        render_questions()
    else:
        render_results()


if __name__ == "__main__":
    main()
