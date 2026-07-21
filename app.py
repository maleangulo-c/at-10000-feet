"""
At 10,000 Feet — Intelligent Automation Maturity Assessment
============================================================
Single-file Streamlit app for Foro MX 2026.

Screens (st.session_state["screen"]): "welcome" | "motivation" | "questions" | "results".
Language (st.session_state["lang"]): "en" | "es".

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
# PILLARS — canonical, language-independent ids (also used as CSV column stems)
# ===========================================================================
PILLARS: list[str] = ["strategy", "people", "opex", "connectivity", "intelligence"]

PILLAR_ICONS: dict[str, str] = {
    "strategy": "🎯",
    "people": "👥",
    "opex": "⚙️",
    "connectivity": "🔗",
    "intelligence": "🧠",
}

# Per-dimension accent colors for the radar chart.
PILLAR_COLORS: dict[str, str] = {
    "strategy": "#E91E8C",      # magenta/pink
    "people": "#1B3B6F",        # navy
    "opex": "#4CAF50",          # green
    "connectivity": "#B8CBFA",  # periwinkle
    "intelligence": "#FFC107",  # gold
}

# Pale gray "halo" showing the full 0-5 range behind each dimension's wedge.
RADAR_TRACK_COLOR = "#EFEFEF"

PILLAR_NAMES: dict[str, dict[str, str]] = {
    "en": {
        "strategy": "Strategy",
        "people": "People",
        "opex": "Operational Excellence",
        "connectivity": "Connectivity",
        "intelligence": "Intelligence",
    },
    "es": {
        "strategy": "Estrategia",
        "people": "Personas",
        "opex": "Excelencia Operativa",
        "connectivity": "Conectividad",
        "intelligence": "Inteligencia",
    },
}

# The question shown next to each category name (welcome screen + assessment header).
PILLAR_QUESTION: dict[str, dict[str, str]] = {
    "en": {
        "strategy": "Are you investing in the right opportunities?",
        "people": "Can your people drive and sustain change?",
        "opex": "Do you control and continuously improve operations?",
        "connectivity": "Can information flow across your factory and business?",
        "intelligence": "How intelligent is your Factory?",
    },
    "es": {
        "strategy": "¿Estás invirtiendo en las oportunidades correctas?",
        "people": "¿Tu gente puede impulsar y sostener el cambio?",
        "opex": "¿Controlas y mejoras continuamente tus operaciones?",
        "connectivity": "¿Puede la información fluir a través de tu planta y tu negocio?",
        "intelligence": "¿Qué tan inteligente es tu fábrica?",
    },
}

# ===========================================================================
# PILLAR_LEVELS — the 0-5 maturity ladder shown on the slider for each
# category. Index 0 is always "Don't know / not sure". Descriptions marked
# "Lorem ipsum dolor sit amet" are placeholders to be replaced later.
# ===========================================================================
PILLAR_LEVELS: dict[str, dict[str, list[dict]]] = {
    "en": {
        "strategy": [
            {"name": "Don't know / not sure", "description": ""},
            {"name": "Awareness of pain points and business losses", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Digital strategy", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Transformation Roadmap", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Investment prioritization", "description": "business case"},
            {"name": "Digital board", "description": "KPI tracking and value measurement"},
        ],
        "people": [
            {"name": "Don't know / not sure", "description": ""},
            {"name": "Capability assessment", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Training", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Collaboration", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Leadership sponsorship", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Change management", "description": "Lorem ipsum dolor sit amet"},
        ],
        "opex": [
            {"name": "Don't know / not sure", "description": ""},
            {"name": "Corrective actions", "description": "firefighting"},
            {"name": "Standard & documented procedures", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Performance management", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Preventive improvement", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Continuous improvement culture", "description": "Lorem ipsum dolor sit amet"},
        ],
        "connectivity": [
            {"name": "Don't know / not sure", "description": ""},
            {"name": "Know your installed base", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Up-to-date automation and production control", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Connected assets and data collection", "description": "Lorem ipsum dolor sit amet"},
            {"name": "OT/IT integration", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Secure connected enterprise", "description": "Cyber security?"},
        ],
        "intelligence": [
            {"name": "Don't know / not sure", "description": ""},
            {"name": "Visibility", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Control and monitoring", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Digital workflow", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Data-driven decision making", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Predictive intelligence", "description": "Lorem ipsum dolor sit amet"},
        ],
    },
    "es": {
        "strategy": [
            {"name": "No sé / no estoy seguro", "description": ""},
            {"name": "Conciencia de puntos de dolor y pérdidas de negocio", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Estrategia digital", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Hoja de ruta de transformación", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Priorización de inversión", "description": "caso de negocio"},
            {"name": "Tablero digital", "description": "seguimiento de KPI y medición de valor"},
        ],
        "people": [
            {"name": "No sé / no estoy seguro", "description": ""},
            {"name": "Evaluación de capacidades", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Capacitación", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Colaboración", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Patrocinio de liderazgo", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Gestión del cambio", "description": "Lorem ipsum dolor sit amet"},
        ],
        "opex": [
            {"name": "No sé / no estoy seguro", "description": ""},
            {"name": "Acciones correctivas", "description": "apagar incendios"},
            {"name": "Procedimientos estándar y documentados", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Gestión del desempeño", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Mejora preventiva", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Cultura de mejora continua", "description": "Lorem ipsum dolor sit amet"},
        ],
        "connectivity": [
            {"name": "No sé / no estoy seguro", "description": ""},
            {"name": "Conoce tu base instalada", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Automatización y control de producción actualizados", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Activos conectados y recolección de datos", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Integración OT/IT", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Empresa conectada segura", "description": "¿Ciberseguridad?"},
        ],
        "intelligence": [
            {"name": "No sé / no estoy seguro", "description": ""},
            {"name": "Visibilidad", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Control y monitoreo", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Flujo de trabajo digital", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Toma de decisiones basada en datos", "description": "Lorem ipsum dolor sit amet"},
            {"name": "Inteligencia predictiva", "description": "Lorem ipsum dolor sit amet"},
        ],
    },
}


def get_pillar_steps(lang: str, pillar: str) -> list[dict]:
    """Build the 5-step maturity ladder (0→1 .. 4→5) for the Recommendations tab,
    reusing the same level names/descriptions shown on the assessment slider."""
    levels = PILLAR_LEVELS[lang][pillar]
    return [
        {
            "transition": f"{i}→{i + 1}",
            "title": levels[i + 1]["name"],
            "description": levels[i + 1]["description"],
            "factory_os": "no",
        }
        for i in range(5)
    ]


# ===========================================================================
# LEVELS — point ranges are language-independent; name/description are not.
# Total score ranges from 0 to len(PILLARS) * 5 (one 0-5 slider per pillar).
# ===========================================================================
TOTAL_MAX = len(PILLARS) * 5

LEVELS_META: list[dict] = [
    {"min": 0, "max": 3, "num": 0},
    {"min": 4, "max": 7, "num": 1},
    {"min": 8, "max": 12, "num": 2},
    {"min": 13, "max": 16, "num": 3},
    {"min": 17, "max": 21, "num": 4},
    {"min": 22, "max": 25, "num": 5},
]

LEVELS_TEXT: dict[str, list[dict]] = {
    "en": [
        {"name": "INACTIVE",
         "description": "Isolated systems, unreliable data, legacy infrastructure, no clear budget or training. Ad-hoc processes with no continuous improvement: you are not ready for digital transformation."},
        {"name": "REACTIVE",
         "description": "Partial data and infrastructure, reactive investment with no business case, resistant team. You're moving slowly without a clear strategy: you need a roadmap and a dedicated team."},
        {"name": "ACTIVE",
         "description": "Integrated systems, clear priorities, approved budget, team in transition, documented processes. You're on the path: modernize infrastructure and raise data governance."},
        {"name": "ESTABLISHED",
         "description": "Reliable data, integrated infrastructure, roadmap with clear financing, trained team, stable operations. You're ready for AI: you can invest in automation with confidence."},
        {"name": "INTEGRATED",
         "description": "Strategic data, modern infrastructure, monitored investment, talent center of excellence, data-driven improvement. You're a benchmark: your focus is continuous innovation."},
        {"name": "PROACTIVE",
         "description": "Mature data ecosystem, zero-trust infrastructure, reinvestment-based financing, learning-first talent, integrated AI. You're an industry leader: you lead ecosystem transformation."},
    ],
    "es": [
        {"name": "INACTIVO",
         "description": "Sistemas aislados, datos poco confiables, infraestructura obsoleta, sin presupuesto ni capacitación claros. Procesos improvisados sin mejora continua: no estás listo para la transformación digital."},
        {"name": "REACTIVO",
         "description": "Datos e infraestructura parciales, inversión reactiva sin caso de negocio, equipo resistente. Avanzas lentamente sin una estrategia clara: necesitas una hoja de ruta y un equipo dedicado."},
        {"name": "ACTIVO",
         "description": "Sistemas integrados, prioridades claras, presupuesto aprobado, equipo en transición, procesos documentados. Vas por buen camino: moderniza la infraestructura y eleva la gobernanza de datos."},
        {"name": "ESTABLECIDO",
         "description": "Datos confiables, infraestructura integrada, hoja de ruta con financiamiento claro, equipo capacitado, operaciones estables. Estás listo para la IA: puedes invertir en automatización con confianza."},
        {"name": "INTEGRADO",
         "description": "Datos estratégicos, infraestructura moderna, inversión monitoreada, centro de excelencia de talento, mejora basada en datos. Eres un referente: tu enfoque es la innovación continua."},
        {"name": "PROACTIVO",
         "description": "Ecosistema de datos maduro, infraestructura de confianza cero, financiamiento basado en reinversión, talento con mentalidad de aprendizaje continuo, IA integrada. Eres líder de la industria: lideras la transformación del ecosistema."},
    ],
}


def get_level(total: int, lang: str) -> dict:
    """Return the merged (meta + text) level entry for a total score."""
    for meta in LEVELS_META:
        if meta["min"] <= total <= meta["max"]:
            text = LEVELS_TEXT[lang][meta["num"]]
            return {**meta, **text}
    meta = LEVELS_META[-1]
    return {**meta, **LEVELS_TEXT[lang][meta["num"]]}


def level_name(num: int, lang: str) -> str:
    return LEVELS_TEXT[lang][num]["name"]


# ===========================================================================
# UI STRINGS
# ===========================================================================
UI: dict[str, dict[str, str]] = {
    "en": {
        "title": "At 10,000 Feet: How Ready Are You for Intelligent Transition?",
        "intro1": (
            "This self-diagnostic helps you understand how prepared your operation is "
            "for **intelligent automation**. In a few minutes you'll rate your maturity "
            "across five dimensions and receive a normalized profile, your overall "
            "readiness level, and a personalized roadmap of next moves."
        ),
        "pillars_prefix": "The five dimensions are: ",
        "step_answer": "Answer",
        "step_calculate": "Calculate",
        "step_review": "Review",
        "tell_us": "Tell us about you",
        "full_name": "Full name *",
        "work_email": "Work email *",
        "company": "Company *",
        "role": "Role / title *",
        "consent_label": "Data treatment policy *",
        "consent_agree": "I confirm I agree with TetraPak's data treatment policy.",
        "consent_decline": (
            "I want to do the exercise, but I don't want to share my data with TetraPak. "
            "By selecting this, I confirm I will not receive strategic information about "
            "solutions I could get through TetraPak to advance my intelligent transformation."
        ),
        "invalid_email": "Please enter a valid email address.",
        "start_assessment": "Start Assessment",
        "motivation_question": "What is your main goal or motivation to advance in the intelligent transition?",
        "motivation_placeholder": "Write your answer here...",
        "continue": "Continue",
        "questions_intro": "Move each slider to the maturity level that best describes your organization today.",
        "back": "← Back",
        "calc_score": "Calculate My Score",
        "results_for": "Results for {name} — {company}",
        "tab_overview": "Overview",
        "tab_reco": "Recommendations",
        "readiness_eq": "#### Your readiness equation",
        "snapshot": "#### A snapshot of your maturity level",
        "your_level": "#### Your level",
        "your_readiness": "YOUR READINESS",
        "points": "Points",
        "level": "Level",
        "level_name_col": "Level Name",
        "level_header": "Level {num} — {name}",
        "reco_intro": (
            "Based on your scores, here's the maturity ladder for each pillar. "
            "✅ Achieved  ·  ▶️ Your next move  ·  ○ Future targets."
        ),
        "mastered": "You've mastered this pillar. Focus on sustaining excellence.",
        "pillar_level_header": "{pillar} — Level {num} ({name})",
        "factoryos_title": "How FactoryOS accelerates you",
        "factoryos_body": (
            "<b>{accel}</b> of your <b>{total}</b> remaining recommended "
            "actions can be accelerated with FactoryOS."
        ),
        "badge_full": "Full",
        "badge_partial": "Partial",
        "learn_more": "Learn more about FactoryOS →",
        "start_over": "Start Over",
        "dev_warning": (
            "⚠️ Dev mode: Google Sheets not configured. "
            "Submissions are being written to `{csv}`."
        ),
        "live_title": "🛫 Live Results — At 10,000 Feet",
        "live_count": "{count} submissions so far · refreshes automatically",
        "live_empty": "No submissions yet. This view refreshes automatically as people complete the assessment.",
    },
    "es": {
        "title": "A 10,000 Pies: ¿Qué Tan Listo Estás para la Transición Inteligente?",
        "intro1": (
            "Este autodiagnóstico te ayuda a entender qué tan preparada está tu operación "
            "para la **automatización inteligente**. En unos minutos calificarás tu madurez "
            "en cinco dimensiones y recibirás un perfil normalizado, tu nivel de "
            "preparación general y una hoja de ruta personalizada de próximos pasos."
        ),
        "pillars_prefix": "Las cinco dimensiones son: ",
        "step_answer": "Responder",
        "step_calculate": "Calcular",
        "step_review": "Revisar",
        "tell_us": "Cuéntanos sobre ti",
        "full_name": "Nombre completo *",
        "work_email": "Correo corporativo *",
        "company": "Empresa *",
        "role": "Puesto / cargo *",
        "consent_label": "Política de tratamiento de datos *",
        "consent_agree": "Confirmo estar de acuerdo con la política de tratamiento de datos de TetraPak.",
        "consent_decline": (
            "Quiero hacer el ejercicio pero no quiero compartir mis datos con TetraPak. "
            "Al marcar esto, confirmo que no recibiré información estratégica sobre las "
            "soluciones que pudiera obtener por medio de TetraPak para avanzar en mi "
            "transformación inteligente."
        ),
        "invalid_email": "Por favor ingresa un correo electrónico válido.",
        "start_assessment": "Iniciar Evaluación",
        "motivation_question": "¿Cuál es tu principal objetivo o motivación para avanzar en la transición inteligente?",
        "motivation_placeholder": "Escribe tu respuesta aquí...",
        "continue": "Continuar",
        "questions_intro": "Mueve cada control deslizante al nivel de madurez que mejor describa a tu organización hoy.",
        "back": "← Atrás",
        "calc_score": "Calcular Mi Puntaje",
        "results_for": "Resultados para {name} — {company}",
        "tab_overview": "Resumen",
        "tab_reco": "Recomendaciones",
        "readiness_eq": "#### Tu ecuación de preparación",
        "snapshot": "#### Una vista de tu nivel de madurez",
        "your_level": "#### Tu nivel",
        "your_readiness": "TU PREPARACIÓN",
        "points": "Puntos",
        "level": "Nivel",
        "level_name_col": "Nombre del Nivel",
        "level_header": "Nivel {num} — {name}",
        "reco_intro": (
            "Según tus puntajes, esta es la escalera de madurez para cada pilar. "
            "✅ Logrado  ·  ▶️ Tu próximo paso  ·  ○ Metas futuras."
        ),
        "mastered": "Has dominado este pilar. Enfócate en mantener la excelencia.",
        "pillar_level_header": "{pillar} — Nivel {num} ({name})",
        "factoryos_title": "Cómo FactoryOS te acelera",
        "factoryos_body": (
            "<b>{accel}</b> de tus <b>{total}</b> acciones recomendadas "
            "restantes pueden acelerarse con FactoryOS."
        ),
        "badge_full": "Completo",
        "badge_partial": "Parcial",
        "learn_more": "Conoce más sobre FactoryOS →",
        "start_over": "Comenzar de Nuevo",
        "dev_warning": (
            "⚠️ Modo desarrollo: Google Sheets no está configurado. "
            "Los envíos se están guardando en `{csv}`."
        ),
        "live_title": "🛫 Resultados en Vivo — At 10,000 Feet",
        "live_count": "{count} respuestas hasta ahora · se actualiza automáticamente",
        "live_empty": "Aún no hay respuestas. Esta vista se actualiza automáticamente conforme la gente completa la evaluación.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Look up a UI string for the given language and format it."""
    text = UI[lang][key]
    return text.format(**kwargs) if kwargs else text


# ===========================================================================
# STYLE constants
# ===========================================================================
PRIMARY = "#7B9BC9"
CAPSULE_FILL = "#B8CCE4"
ACCENT = "#7B9BC9"


# ===========================================================================
# SCORING LOGIC
# ===========================================================================
def pillar_max(pillar: str) -> int:
    """Max level for a pillar (0-5 slider)."""
    return 5


# ===========================================================================
# ANALYTICS — persistence
# ===========================================================================
SHEET_HEADER = (
    ["timestamp_iso", "share_data", "name", "company", "email", "role", "motivation", "language"]
    + [f"{p}_level" for p in PILLARS]
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


def build_row(profile: dict, answers: dict, lang: str) -> list:
    """Assemble one analytics row in the fixed column order.

    Level/pillar names are always stored in English for consistent analytics,
    regardless of which language the respondent used. When the respondent
    declined to share their data with TetraPak, name/company/email/role/
    motivation are omitted (blank) but the pillar answers/scores are still
    recorded so aggregate Foro MX stats stay complete.
    """
    share_data = profile.get("share_data", True)
    levels = [sum(answers[p]) for p in PILLARS]  # each answers[p] is a 1-item list holding the selected level (0-5)
    total = sum(levels)
    lvl = get_level(total, "en")
    pii = (
        [profile["name"], profile["company"], profile["email"], profile["role"], profile.get("motivation", "")]
        if share_data else ["", "", "", "", ""]
    )
    return (
        [
            datetime.now(timezone.utc).isoformat(),
            "yes" if share_data else "no",
        ]
        + pii
        + [lang]
        + levels
        + [total, lvl["num"], lvl["name"]]
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


@st.cache_data(ttl=10, show_spinner=False)
def _fetch_all_submissions() -> list[dict]:
    """Fetch every persisted submission row (Google Sheets if configured,
    else the local CSV fallback) for the live-results aggregate.

    Cached for a short TTL so every simultaneous viewer of the live view
    shares one read instead of hammering the Sheets API each refresh.
    """
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

    # Local-dev fallback.
    if not os.path.exists(LOCAL_CSV):
        return []
    with open(LOCAL_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _compute_live_aggregate() -> dict:
    """Average maturity level per pillar across every submission so far."""
    rows = _fetch_all_submissions()
    count = len(rows)
    if count == 0:
        return {"count": 0, "averages": {p: 0.0 for p in PILLARS}, "total_avg": 0.0}

    averages = {}
    for pillar in PILLARS:
        col = f"{pillar}_level"
        values = [float(r[col]) for r in rows if str(r.get(col, "")).strip() != ""]
        averages[pillar] = round(sum(values) / len(values), 1) if values else 0.0
    total_avg = round(sum(averages.values()), 1)
    return {"count": count, "averages": averages, "total_avg": total_avg}


# ===========================================================================
# SESSION STATE INIT
# ===========================================================================
def init_state() -> None:
    st.session_state.setdefault("screen", "welcome")
    st.session_state.setdefault("lang", "en")
    st.session_state.setdefault("profile", {})
    # answers[pillar] = [level], a 1-item list holding the selected 0-5 maturity level.
    # Default is 0 ("Don't know / not sure"), a legitimate answer on its own.
    if "answers" not in st.session_state:
        st.session_state["answers"] = {p: [0] for p in PILLARS}


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


def render_language_switcher() -> None:
    """Small language selector shown top-right on every screen."""
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
# SCREEN 1 — Welcome + participant info
# ===========================================================================
def render_welcome() -> None:
    lang = st.session_state["lang"]
    st.title(t(lang, "title"))

    st.markdown(t(lang, "intro1"))

    pillars_line = t(lang, "pillars_prefix") + " · ".join(
        f"**{PILLAR_NAMES[lang][p]}**" for p in PILLARS
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

    st.subheader(t(lang, "tell_us"))
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input(t(lang, "full_name"), key="in_name")
        email = st.text_input(t(lang, "work_email"), key="in_email")
    with col2:
        company = st.text_input(t(lang, "company"), key="in_company")
        role = st.text_input(t(lang, "role"), key="in_role")

    st.markdown(f"<strong>{t(lang, 'consent_label')}</strong>", unsafe_allow_html=True)
    consent_choice = st.radio(
        t(lang, "consent_label"),
        options=["agree", "decline"],
        format_func=lambda x: t(lang, "consent_agree") if x == "agree" else t(lang, "consent_decline"),
        index=None,
        key="in_consent_choice",
        label_visibility="collapsed",
    )

    email_ok = bool(EMAIL_RE.match(email.strip())) if email else False
    if email and not email_ok:
        st.caption(f":red[{t(lang, 'invalid_email')}]")

    all_filled = all(v.strip() for v in (name, company, email, role))
    can_start = all_filled and email_ok and consent_choice is not None

    if st.button(t(lang, "start_assessment"), type="primary", disabled=not can_start):
        st.session_state["profile"] = {
            "name": name.strip(),
            "company": company.strip(),
            "email": email.strip(),
            "role": role.strip(),
            "share_data": consent_choice == "agree",
        }
        st.session_state["screen"] = "motivation"
        st.rerun()


# ===========================================================================
# SCREEN 1B — Motivation
# ===========================================================================
def render_motivation() -> None:
    lang = st.session_state["lang"]
    st.subheader(t(lang, "motivation_question"))

    current = st.session_state["profile"].get("motivation", "")
    answer = st.text_area(
        t(lang, "motivation_question"),
        value=current,
        placeholder=t(lang, "motivation_placeholder"),
        key="in_motivation",
        label_visibility="collapsed",
        height=150,
    )
    can_continue = bool(answer.strip())

    cols = st.columns([1, 3])
    with cols[0]:
        if st.button(t(lang, "back"), key="back_to_welcome_from_motivation"):
            st.session_state["screen"] = "welcome"
            st.rerun()
    with cols[1]:
        if st.button(t(lang, "continue"), type="primary", disabled=not can_continue):
            st.session_state["profile"]["motivation"] = answer.strip()
            st.session_state["screen"] = "questions"
            st.rerun()


# ===========================================================================
# SCREEN 2 — Questionnaire
# ===========================================================================
# Step-line slider accent — a thin line connecting 6 stops (open circles),
# with the selected stop shown as a bigger filled circle (the native thumb).
_SLIDER_ACCENT = "#4A72B5"

# The 5 unselected stops are painted directly onto the native track's own
# background (as small ring "donuts" at the 0/20/40/60/80/100% points, the
# same points the thumb travels between) plus a thin connecting line. The
# selected stop needs no separate drawing — the native thumb already sits
# exactly on top of it, so it's just styled as the bigger filled circle.
_DOT = f'radial-gradient(circle closest-side, #FFFFFF 60%, {_SLIDER_ACCENT} 62%, {_SLIDER_ACCENT} 92%, transparent 94%)'
_TRACK_BG = ",\n        ".join([_DOT] * 6 + [f"linear-gradient({_SLIDER_ACCENT}, {_SLIDER_ACCENT})"])
_TRACK_POS = "0% 50%, 20% 50%, 40% 50%, 60% 50%, 80% 50%, 100% 50%, center"
_TRACK_SIZE = "16px 16px, 16px 16px, 16px 16px, 16px 16px, 16px 16px, 16px 16px, 100% 2px"

_SLIDER_CSS = f"""
<style>
div[data-testid="stSlider"] {{ padding-top: 6px; }}
div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child {{
    background-image: {_TRACK_BG} !important;
    background-position: {_TRACK_POS} !important;
    background-size: {_TRACK_SIZE} !important;
    background-repeat: no-repeat !important;
    height: 20px !important;
    border-radius: 0 !important;
}}
div[data-testid="stSlider"] div[data-baseweb="slider"] > div:nth-child(2) {{
    background: transparent !important;
}}
/* Streamlit's own "filled range" indicator (min→value), nested one level
   deeper than the track itself — neutralize it so only our dots/line show. */
div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child > div {{
    background: transparent !important;
    background-image: none !important;
}}
div[data-testid="stSlider"] div[role="slider"] {{
    background-color: {_SLIDER_ACCENT} !important;
    border: none !important;
    width: 26px !important;
    height: 26px !important;
    box-shadow: none !important;
}}
/* Below ~640px (phones), the 6 level labels can't fit side by side without
   wrapping past their fixed-height row and overlapping the next card — stack
   them into a plain vertical list instead of positioning them absolutely. */
@media (max-width: 640px) {{
    .pv-row {{
        position: static !important;
        height: auto !important;
        padding: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 10px !important;
    }}
    .pv-cell {{
        position: static !important;
        width: 100% !important;
        left: auto !important;
        right: auto !important;
        transform: none !important;
        text-align: left !important;
        padding: 4px 2px !important;
    }}
}}
</style>
"""


def _pillar_level_labels_html(levels: list[dict]) -> str:
    """Render the 0-5 label row under a pillar's slider: number, bold title,
    italic "(description)" (level 0 has none). Selection is shown by the dot
    above (the bigger filled stop), not by highlighting a label, so every
    label uses the same plain style. Labels sit at the exact 0/20/40/60/80/100%
    points the slider's 6 stops sit at (not 6 equal-width cells), so each
    stays lined up with its dot."""
    n = len(levels)
    slot = 100 / n  # cell width, close to the 1/6 spacing between stops
    cells = []
    for i, level in enumerate(levels):
        desc = (
            f'<div style="font-size:0.78rem;font-style:italic;color:#666;margin-top:2px;">({level["description"]})</div>'
            if level["description"] else ""
        )
        body = (
            f'<div style="font-size:0.82rem;font-weight:700;color:#1A1A1A;">{level["name"]}</div>'
            + desc
        )
        pct = i / (n - 1) * 100
        if i == 0:
            pos = f"left:0%; text-align:left;"
        elif i == n - 1:
            pos = f"right:0%; text-align:right;"
        else:
            pos = f"left:{pct}%; transform:translateX(-50%); text-align:center;"
        cells.append(
            f'<div class="pv-cell" style="position:absolute;{pos}top:0;width:{slot}%;padding:6px 4px;box-sizing:border-box;">'
            f'<div style="font-size:0.78rem;color:#888;margin-bottom:2px;">{i}.</div>'
            f'{body}'
            f'</div>'
        )
    return (
        '<div class="pv-row" style="position:relative;height:72px;margin-top:8px;padding:0 9px;box-sizing:border-box;">'
        + "".join(cells)
        + '</div>'
    )


def render_questions() -> None:
    lang = st.session_state["lang"]
    st.markdown(_SLIDER_CSS, unsafe_allow_html=True)
    st.markdown(t(lang, "questions_intro"))
    st.markdown("")

    for pillar in PILLARS:
        levels = PILLAR_LEVELS[lang][pillar]
        with st.container(border=True):
            st.markdown(f"**{PILLAR_NAMES[lang][pillar]}** — {PILLAR_QUESTION[lang][pillar]}")
            current = st.session_state["answers"][pillar][0]
            value = st.select_slider(
                PILLAR_NAMES[lang][pillar],
                options=[0, 1, 2, 3, 4, 5],
                value=current,
                key=f"pillar_{pillar}",
                label_visibility="collapsed",
                format_func=lambda x: "",  # hide the native value tooltip/endpoint labels
            )
            st.session_state["answers"][pillar][0] = value
            st.markdown(_pillar_level_labels_html(levels), unsafe_allow_html=True)
        st.markdown("")

    st.divider()
    cols = st.columns([1, 3])
    with cols[0]:
        if st.button(t(lang, "back"), key="back_to_welcome"):
            st.session_state["screen"] = "welcome"
            st.rerun()
    with cols[1]:
        if st.button(t(lang, "calc_score"), type="primary"):
            persist_submission(st.session_state["profile"], st.session_state["answers"], lang)
            st.session_state["screen"] = "results"
            st.session_state["scroll_top"] = True
            st.rerun()


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


def render_equation_block(answers: dict, total: int, lvl: dict, lang: str) -> None:
    raws = {p: sum(answers[p]) for p in PILLARS}

    items = [
        _score_item_html(
            "🛫", f"{total}", f"/{TOTAL_MAX}", f"{t(lang, 'your_readiness')} — {lvl['name']}", total=True
        )
    ]
    for pillar in PILLARS:
        pmax = pillar_max(pillar)
        items.append(
            _score_item_html(
                PILLAR_ICONS[pillar], f"{raws[pillar]}", f"/{pmax}", PILLAR_NAMES[lang][pillar], total=False
            )
        )

    html = (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;padding:8px 0;">'
        + "".join(items)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_radar(answers: dict, lang: str) -> None:
    """Polar bar chart: each dimension is a pie wedge, gapped from its
    neighbors, in a flat accent color, sitting over a pale gray halo that
    shows the full 0-5 range. Radius (0 at center, 5 at the outer ring)
    encodes the dimension's score."""
    n = len(PILLARS)
    sector = 360 / n
    gap = 8  # degrees of visible gap between wedges
    bar_width = sector - gap
    centers = [i * sector for i in range(n)]

    values = [sum(answers[p]) for p in PILLARS]  # raw 0-5 score per pillar
    labels = [f"{PILLAR_ICONS[p]}<br>{PILLAR_NAMES[lang][p]}" for p in PILLARS]

    fig = go.Figure()
    # Pale gray halo: every wedge at full radius (5), no border.
    fig.add_trace(
        go.Barpolar(
            r=[5] * n,
            theta=centers,
            width=[bar_width] * n,
            marker_color=RADAR_TRACK_COLOR,
            marker_line_width=0,
            hoverinfo="skip",
            showlegend=False,
        )
    )
    # Data wedges: flat accent color per pillar, no border.
    fig.add_trace(
        go.Barpolar(
            r=values,
            theta=centers,
            width=[bar_width] * n,
            marker_color=[PILLAR_COLORS[p] for p in PILLARS],
            marker_line_width=0,
            customdata=[PILLAR_NAMES[lang][p] for p in PILLARS],
            hovertemplate="%{customdata}: %{r}/5<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        polar=dict(
            barmode="overlay",  # the halo and data wedges overlay, not stack
            radialaxis=dict(
                range=[0, 5],
                tickvals=[1, 2, 3, 4, 5],
                showticklabels=True,
                gridcolor="#E5E5E5",
                linecolor="#E5E5E5",
                tickfont=dict(size=11, color="#666666"),
            ),
            angularaxis=dict(
                tickmode="array",
                tickvals=centers,
                ticktext=labels,
                direction="clockwise",
                rotation=90,
                showgrid=False,
                linecolor="rgba(0,0,0,0)",
                tickfont=dict(size=15, color="#000000"),
            ),
            bgcolor="#FFFFFF",
        ),
        showlegend=False,
        margin=dict(l=80, r=80, t=50, b=50),
        height=460,
        paper_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_level_table(lvl: dict, lang: str) -> None:
    rows = []
    for meta in LEVELS_META:
        text = LEVELS_TEXT[lang][meta["num"]]
        achieved = meta["num"] == lvl["num"]
        pts = f"{meta['min']}–{meta['max']}"
        if achieved:
            rows.append(
                f'<tr style="background:{CAPSULE_FILL};font-weight:700;">'
                f'<td style="padding:6px 10px;">{pts}</td>'
                f'<td style="padding:6px 10px;">L{meta["num"]}</td>'
                f'<td style="padding:6px 10px;">{text["name"]}</td></tr>'
            )
        else:
            rows.append(
                f'<tr><td style="padding:6px 10px;color:#555;">{pts}</td>'
                f'<td style="padding:6px 10px;color:#555;">L{meta["num"]}</td>'
                f'<td style="padding:6px 10px;color:#555;">{text["name"]}</td></tr>'
            )
    table = (
        '<table style="border-collapse:collapse;width:100%;font-size:0.92rem;">'
        '<thead><tr style="border-bottom:2px solid #ccc;">'
        f'<th style="text-align:left;padding:6px 10px;">{t(lang, "points")}</th>'
        f'<th style="text-align:left;padding:6px 10px;">{t(lang, "level")}</th>'
        f'<th style="text-align:left;padding:6px 10px;">{t(lang, "level_name_col")}</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )
    st.markdown(table, unsafe_allow_html=True)


def render_overview_tab(answers: dict, total: int, lvl: dict, lang: str) -> None:
    st.markdown(t(lang, "readiness_eq"))
    render_equation_block(answers, total, lvl, lang)
    st.divider()

    st.markdown(t(lang, "snapshot"))
    render_radar(answers, lang)
    st.divider()

    st.markdown(t(lang, "your_level"))
    c1, c2 = st.columns([1, 1.3])
    with c1:
        render_level_table(lvl, lang)
    with c2:
        st.markdown(
            f'<div style="font-size:1.15rem;font-weight:700;color:{PRIMARY};">'
            f'{t(lang, "level_header", num=lvl["num"], name=lvl["name"])}</div>',
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


def render_recommendations_tab(answers: dict, lang: str) -> None:
    st.markdown(t(lang, "reco_intro"))

    # Track FactoryOS acceleration data while rendering ladders.
    forward_total = 0
    accelerated: dict[str, list[dict]] = {}

    for pillar in PILLARS:
        p_level = sum(answers[pillar])  # answers[pillar] is a 1-item list holding the selected level
        steps = get_pillar_steps(lang, pillar)
        p_level_name = PILLAR_LEVELS[lang][pillar][p_level]["name"]

        st.markdown(
            f"### {t(lang, 'pillar_level_header', pillar=PILLAR_NAMES[lang][pillar], num=p_level, name=p_level_name)}"
        )

        if p_level == 5:
            st.markdown(f":green[**{t(lang, 'mastered')}**]")

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
        f'{t(lang, "factoryos_title")}</div>',
        f'<div style="font-size:1.02rem;color:#333;margin-bottom:14px;">'
        f'{t(lang, "factoryos_body", accel=accel_count, total=forward_total)}</div>',
    ]

    for pillar in PILLARS:
        if pillar not in accelerated:
            continue
        box.append(
            f'<div style="font-weight:700;color:#1A1A1A;margin:10px 0 4px;">{PILLAR_NAMES[lang][pillar]}</div>'
        )
        for step in accelerated[pillar]:
            if step["factory_os"] == "yes":
                badge = (f'<span style="background:#E8F5E9;color:#2E7D32;border-radius:8px;'
                         f'padding:2px 8px;font-size:0.72rem;font-weight:700;margin-left:8px;">{t(lang, "badge_full")}</span>')
            else:
                badge = (f'<span style="background:#FFF3E0;color:#E65100;border-radius:8px;'
                         f'padding:2px 8px;font-size:0.72rem;font-weight:700;margin-left:8px;">{t(lang, "badge_partial")}</span>')
            box.append(
                f'<div style="color:#333;font-size:0.94rem;margin:2px 0 2px 8px;">'
                f'• {step["title"]}{badge}</div>'
            )

    box.append('</div>')
    st.markdown("".join(box), unsafe_allow_html=True)

    st.markdown("")
    st.link_button(t(lang, "learn_more"), "#", type="primary")


def render_results() -> None:
    lang = st.session_state["lang"]

    # Jump to the top once, right after arriving from the questionnaire.
    if st.session_state.pop("scroll_top", False):
        scroll_to_top()

    answers = st.session_state["answers"]
    profile = st.session_state["profile"]
    total = sum(sum(answers[p]) for p in PILLARS)
    lvl = get_level(total, lang)

    st.markdown(f"## {t(lang, 'results_for', name=profile.get('name', ''), company=profile.get('company', ''))}")

    tab_overview, tab_reco = st.tabs([t(lang, "tab_overview"), t(lang, "tab_reco")])
    with tab_overview:
        render_overview_tab(answers, total, lvl, lang)
    with tab_reco:
        render_recommendations_tab(answers, lang)

    st.divider()
    if st.button(t(lang, "start_over")):
        keep_ws = st.session_state.get("gs_worksheet")
        st.session_state.clear()
        if keep_ws is not None:
            st.session_state["gs_worksheet"] = keep_ws
        st.rerun()


# ===========================================================================
# SCREEN 4 — Live Results (organizer/projector view, via ?view=live)
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
        synthetic_answers = {p: [agg["averages"][p]] for p in PILLARS}
        lvl = get_level(agg["total_avg"], lang)

        render_equation_block(synthetic_answers, agg["total_avg"], lvl, lang)
        st.divider()
        render_radar(synthetic_answers, lang)

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
    render_language_switcher()
    lang = st.session_state["lang"]

    # Organizer/projector view — separate from the assessment flow entirely,
    # reachable at ?view=live regardless of the visitor's own screen state.
    if st.query_params.get("view") == "live":
        render_live_results()
        return

    # Dev-only warning when Google Sheets isn't configured.
    if not _has_google_secrets():
        st.sidebar.warning(t(lang, "dev_warning", csv=LOCAL_CSV))

    screen = st.session_state["screen"]
    if screen == "welcome":
        render_welcome()
    elif screen == "motivation":
        render_motivation()
    elif screen == "questions":
        render_questions()
    else:
        render_results()


if __name__ == "__main__":
    main()
