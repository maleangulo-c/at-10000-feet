"""
Sends each participant their results by email via the Resend API
(https://resend.com), right after they finish the assessment.

Never raises — a broken/missing API key or a failed send must not block the
results screen, same fail-safe posture as the Google Sheets persistence in
app.py. Requires `resend_api_key` in st.secrets; `email_from` is optional
(defaults to Resend's no-setup test sender, which works for any recipient
without verifying a domain).
"""

from __future__ import annotations

import data_loader as dl
from translations import (
    DIMENSION_ICONS,
    DIMENSION_NAMES,
    DIMENSION_PRIORITY,
    FALLBACK_SOLUTIONS,
    UI,
    t,
    translate_fw,
)

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "At 10,000 Feet <onboarding@resend.dev>"

PRIMARY = "#2D68F4"
NAVY_TEXT = "#1B2E96"
PALE_BLUE = "#EEF3FF"
BORDER = "#E5E5E5"


def _top_recommendations(answers: dict) -> list[dict]:
    """Same ranking as app.get_top_recommendations, duplicated here to avoid
    importing app.py (which would create a circular import)."""
    assessed = [(d, s) for d, s in answers.items() if s > 0]
    ranked = sorted(assessed, key=lambda ds: (ds[1], -DIMENSION_PRIORITY[ds[0]]))
    top = ranked[:3]
    return [
        {"dimension": d, "current": s, "target": min(s + 1, 5), "mastered": s == 5}
        for d, s in top
    ]


def _solutions_for(framework: dict, dim: str, target_level: int) -> list[dict]:
    solutions_bank = dl.load_workbook_data()["solutions_bank"]
    sols = framework[dim]["solutions"].get(target_level, [])
    if not sols:
        sols = [{"name": name, "vp": None} for name in FALLBACK_SOLUTIONS.get(dim, [])]
    out = []
    for s in sols:
        bank_entry = solutions_bank.get(s["name"], {})
        vp = s.get("vp") or bank_entry.get("vp") or ""
        out.append({"name": s["name"], "vp": vp})
    return out


def _dimension_rows_html(lang: str, answers: dict, framework: dict) -> str:
    rows = []
    for dim, score in answers.items():
        icon = DIMENSION_ICONS[dim]
        name = DIMENSION_NAMES[lang][dim]
        if score == 0:
            level_text = t(lang, "level0_label")
        else:
            level_info = framework[dim]["levels"][score]
            level_text = f"{score} — {translate_fw(lang, level_info['name'])}"
        rows.append(
            f'<tr><td style="padding:8px 12px;border-bottom:1px solid {BORDER};">{icon} {name}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid {BORDER};color:{NAVY_TEXT};font-weight:600;">{level_text}</td></tr>'
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:14px;margin:12px 0 24px;">'
        + "".join(rows)
        + "</table>"
    )


def _recommendations_html(lang: str, answers: dict, framework: dict) -> str:
    top = _top_recommendations(answers)
    if not top:
        return ""

    blocks = []
    for rec in top:
        dim = rec["dimension"]
        icon = DIMENSION_ICONS[dim]
        name = DIMENSION_NAMES[lang][dim]
        if rec["mastered"]:
            body = f'<p style="margin:4px 0 0;color:#333;">{translate_fw(lang, framework[dim]["next_step"])}</p>'
        else:
            solutions = _solutions_for(framework, dim, rec["target"])
            items = "".join(
                f'<li style="margin:4px 0;"><strong>{s["name"]}</strong> — '
                f'<span style="color:#555;">{translate_fw(lang, s["vp"])}</span></li>'
                for s in solutions
            )
            transition = t(lang, "reco_level_transition", current=rec["current"], target=rec["target"])
            body = (
                f'<p style="margin:4px 0 8px;color:{PRIMARY};font-weight:700;">{transition}</p>'
                f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
            )
        blocks.append(
            f'<div style="background:{PALE_BLUE};border-radius:10px;padding:14px 18px;margin-bottom:12px;">'
            f'<div style="font-weight:700;color:{NAVY_TEXT};font-size:15px;">{icon} {name}</div>'
            f"{body}</div>"
        )
    return "".join(blocks)


def build_results_email_html(lang: str, profile: dict, answers: dict, framework: dict) -> tuple[str, str]:
    """Returns (subject, html_body)."""
    name = profile.get("name", "")
    subject = t(lang, "email_subject")
    html = f"""
    <meta charset="utf-8">
    <div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:{PRIMARY};padding:20px 24px;border-radius:10px 10px 0 0;">
        <span style="font-size:22px;">🛫</span>
        <span style="color:#fff;font-size:18px;font-weight:700;margin-left:8px;">{t(lang, "title")}</span>
      </div>
      <div style="border:1px solid {BORDER};border-top:none;border-radius:0 0 10px 10px;padding:24px;">
        <p style="font-size:15px;color:#1A1A1A;">{t(lang, "email_greeting", name=name)}</p>
        <p style="font-size:14px;color:#555;">{t(lang, "email_intro")}</p>
        <h3 style="color:{NAVY_TEXT};font-size:16px;margin-bottom:4px;">{t(lang, "email_dimensions_title")}</h3>
        {_dimension_rows_html(lang, answers, framework)}
        <h3 style="color:{NAVY_TEXT};font-size:16px;margin-bottom:4px;">{t(lang, "email_recommendations_title")}</h3>
        {_recommendations_html(lang, answers, framework)}
        <p style="font-size:12px;color:#999;margin-top:24px;">{t(lang, "email_footer")}</p>
      </div>
    </div>
    """
    return subject, html


def send_results_email(lang: str, profile: dict, answers: dict, framework: dict) -> bool:
    """Sends the results email via Resend. Returns True on success, False on
    any failure (missing secret, network error, API error) — never raises."""
    import streamlit as st

    to_email = profile.get("email", "").strip()
    if not to_email:
        return False

    try:
        api_key = st.secrets["resend_api_key"]
    except Exception:
        return False

    from_addr = st.secrets.get("email_from", DEFAULT_FROM)

    try:
        import requests

        subject, html = build_results_email_html(lang, profile, answers, framework)
        resp = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_addr, "to": [to_email], "subject": subject, "html": html},
            timeout=10,
        )
        return resp.status_code < 300
    except Exception as exc:  # noqa: BLE001
        print(f"[email] send failed: {exc}")
        return False
