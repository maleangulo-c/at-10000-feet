# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page **Streamlit** app ("At 10,000 Feet") for Foro MX 2026 participants to
self-assess their digital-transformation maturity across **5 dimensions** (Strategy,
People, Operations, Connectivity, Intelligence). Users fill in their profile, answer one
maturity question per dimension (levels 0–5), then land on a results screen with a radar
chart vs. an industry MVS (Minimum Viable Status) benchmark, a KPI improvement-potential
table, a prioritized "Next Steps" recommendation section, customer success stories, and a
downloadable PDF report. Every submission is logged to Google Sheets (or a local CSV
fallback) for event analytics. The UI is fully bilingual (English/Spanish).

## Commands

```bash
# install deps
pip install -r requirements.txt

# run locally — opens at http://localhost:8501
streamlit run app.py
```

There is no test suite, linter, or build step configured in this repo — `streamlit run
app.py` (and manually exercising the UI) is the only verification loop.

**Local-dev analytics fallback:** if `.streamlit/secrets.toml` isn't present (see below),
submissions are appended to `./submissions_local.csv` instead of Google Sheets, and a
warning banner shows in the sidebar. No setup is required to try the app locally.

### Google Sheets analytics (production)

Streamlit Community Cloud has an ephemeral filesystem, so the CSV fallback doesn't survive
restarts — production submissions go to a Google Sheet via a service account. Setup is a
GCP service account (Sheets + Drive APIs enabled) whose credentials get copied into
`.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example` for the exact shape:
`sheet_id` + a `[gcp_service_account]` block with the JSON key fields). The sheet must be
shared with the service account's `client_email` as Editor; the app creates the
`submissions` worksheet and header row itself on first write. **Never commit
`secrets.toml`** — only the `.example` template belongs in version control.

Deploying to Streamlit Community Cloud: push to GitHub, create the app at
share.streamlit.io pointing at `app.py`, and paste the full `secrets.toml` contents into
Advanced settings → Secrets.

## Architecture

### The workbook is the single source of truth for content

`Digital_readiness_tool_Framework.xlsx` drives almost everything content-related — the
per-dimension maturity levels/descriptions, the solutions catalog, MVS benchmark values,
MVS-savings ranges per food-category sub-sector, and the customer success stories. To
change any of that content, **edit the workbook, not the code.** `data_loader.py` parses
it once per process (`@st.cache_resource`) into plain dicts/lists via
`load_workbook_data()`; every sheet has a dedicated `_parse_*` function with the exact
column layout it expects (columns are positional, not header-matched, so a reordered
workbook column silently breaks parsing).

### Bilingual content: two different mechanisms

- **Static UI strings** (buttons, labels, headings) live in `translations.py`'s `UI` dict,
  keyed `UI[lang][key]`, looked up via `t(lang, key, **kwargs)` (does `.format()` on the
  string). English and Spanish entries must be kept in sync manually — there's no
  fallback if a key is missing from one language.
- **Workbook-sourced text** (level names/descriptions, dimension questions, solution value
  props) is English-only in the .xlsx. `translate_fw(lang, text)` looks the exact English
  string up in `_ES_LOOKUP` (a flat `{english: spanish}` dict) and falls back to the
  English text if no translation is registered — so adding a new row/level to the
  workbook without adding its Spanish entry to `_ES_LOOKUP` degrades gracefully rather
  than crashing.

### Screen flow is a manual state machine

`app.py` has no router — `st.session_state["screen"]` is one of `welcome | profile |
motivation | assessment | results`, and `main()` dispatches to the matching `render_*`
function. `assessment` is itself sub-paginated by `st.session_state["dim_index"]` (0–4,
one screen per dimension in `DIMENSIONS` order); `answers` is a `{dimension: level}` dict
in session state where `0` means "not assessed" (excluded from the radar, MVS comparisons,
and recommendations — not the same as an unanswered question). Back-navigation from
results goes to `dim_index = len(DIMENSIONS) - 1` rather than resetting state, so editing
answers doesn't lose the profile/motivation already entered.

### Recommendation ranking

`get_top_recommendations()` (app.py) picks the 3 lowest-scoring **assessed** dimensions
(score > 0), tie-broken by `DIMENSION_PRIORITY` (Strategy > Operations > Connectivity >
People > Intelligence — a fixed business priority order, not derived from anything in the
workbook). For each, `get_solutions_for_target()` looks up solutions mapped to that exact
dimension+target-level in the workbook, then tops up from `FALLBACK_SOLUTIONS` and finally
from the dimension's other levels if the exact level has fewer than 3 solutions mapped
(most levels only have 1–2 in the workbook). Customer-story selection follows the same
top-3-dimension list, scored by category/maturity-bucket match, deduped by customer name
**across** dimensions (a story matching two recommended dimensions should only render
once) — this dedup is the part most likely to regress if the loop structure changes.

### PDF report duplicates ranking logic on purpose

`pdf_report.py` is intentionally decoupled from `app.py` (app.py imports it, so the
reverse would be a circular import) — `_top_recommendations`, `_solutions_for`, and
`_top_stories` are near-duplicates of the app.py logic above, not shared helpers. Keep
both in sync by hand if the ranking/dedup rules change. The PDF is built with `fpdf2`
using core Helvetica (no embedded fonts) and hand-drawn vector primitives — the radar
chart, KPI table, and current/target level cards are all drawn with `line`/`rect`/
`ellipse`/`multi_cell` rather than exporting the Plotly figure, specifically to avoid a
Kaleido/headless-Chrome dependency on Streamlit Cloud. Two load-bearing details:
- `fpdf2`'s `multi_cell` defaults to justified text and parks the cursor at the cell's
  *right* edge when done — calling it twice in a row without resetting `x` silently walks
  content off the page. The `_mc()` wrapper pins `align="L"` and `new_x="LMARGIN"` for
  every text block; don't call `pdf.multi_cell` directly in new code.
- Manual drawing (`line`/`rect`/`ellipse`) does **not** trigger fpdf2's automatic page
  break, unlike `cell`/`multi_cell`. Any new hand-drawn block must call `_ensure_space()`
  first or it can render past the bottom margin.
- The Overview page and the Next Steps page are each designed to fit on one sheet — row
  heights, card heights, etc. are computed with `split_only=True` dry-runs rather than
  hardcoded, so content-length changes (e.g. longer workbook text) reflow automatically,
  but a sufficiently long addition can still push either page to a second sheet.

### Analytics row shape

`SHEET_HEADER` in app.py defines the exact column order written to Google Sheets/CSV;
`build_row()` must stay in lockstep with it. If the participant declines to share data
(`share_data=False`), PII (name/company/email/motivation/investment_approach) is blanked
before writing, but dimension scores are still recorded — aggregate stats stay complete
without the individually-identifying fields.
