# At 10,000 Feet — Digital Readiness Assessment

A single-page **Streamlit** app for **Foro MX 2026** participants to self-assess
their digital-transformation maturity across **5 dimensions** — Strategy, People,
Operations, Connectivity, and Intelligence. Users fill in their profile, answer one
maturity question per dimension (levels 0–5), then see a results screen with a radar
chart comparing their scores to an industry MVS (Minimum Viable Status) benchmark,
a KPI improvement-potential table, prioritized "Next Steps" recommendations, customer
success stories, and a downloadable PDF report. Every submission is logged to Google
Sheets (or a local CSV fallback) for event analytics.

The UI is fully bilingual (**English / Spanish**).

---

## 1. Local run

Requires **Python 3.10+**.

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. run
streamlit run app.py
```

The app opens at <http://localhost:8501>.

**Local-dev analytics fallback:** if Google Sheets secrets are not configured
(`.streamlit/secrets.toml` is missing), every submission is appended to
`./submissions_local.csv` and a warning banner is shown in the sidebar. No setup is
required to try the app locally.

---

## 2. Google Sheets analytics setup

Streamlit Community Cloud has an **ephemeral filesystem**, so a local CSV won't survive
restarts. In production, submissions are written to a Google Sheet via a service account.

### Step 1 — Create a GCP service account
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create (or select) a project.
3. **IAM & Admin → Service Accounts → Create service account.**
4. Give it a name (e.g. `foro-mx-analytics`), then **Create and continue → Done**.

### Step 2 — Enable the APIs
In **APIs & Services → Library**, enable both:
- **Google Sheets API**
- **Google Drive API**

### Step 3 — Create a JSON key
1. Open the service account → **Keys → Add key → Create new key → JSON**.
2. A JSON file downloads. You'll copy its fields into `secrets.toml` (Step 5).

### Step 4 — Create and share the target sheet
1. Create a new Google Sheet. Copy its **Sheet ID** from the URL:
   `https://docs.google.com/spreadsheets/d/`**`<THIS_IS_THE_SHEET_ID>`**`/edit`
2. Click **Share** and share the sheet with the service account's
   `client_email` (e.g. `foro-mx-analytics@your-project.iam.gserviceaccount.com`)
   as an **Editor**.
3. The app creates a worksheet named `submissions` and its header row automatically
   on the first write.

### Step 5 — Populate secrets
Copy the template and fill in the values from your JSON key file:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:
- `sheet_id` — the Sheet ID from Step 4.
- `[gcp_service_account]` — paste each field from the downloaded JSON. Keep the
  `private_key` on one line with literal `\n` escapes exactly as they appear in the JSON.

> **Never commit `secrets.toml`.** Only the `.example` template belongs in version control.

---

## 3. Deploy to Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select the repo/branch and set the main file to `app.py`.
4. In **Advanced settings → Secrets**, paste the full contents of your
   `.streamlit/secrets.toml` (the same TOML format, including the
   `[gcp_service_account]` block and `sheet_id`).
5. Deploy. Submissions will flow into your Google Sheet's `submissions` worksheet.

---

## 4. Content & translations

### Workbook as single source of truth

`Digital_readiness_tool_Framework.xlsx` drives all content — per-dimension maturity
levels and descriptions, the solutions catalog, MVS benchmark values, MVS-savings ranges
per food-category sub-sector, and customer success stories. To change any content,
**edit the workbook, not the code.** `data_loader.py` parses it once per process and
caches the result.

### Bilingual content

Two mechanisms:

| What | Where | How |
|---|---|---|
| Static UI strings (buttons, labels, headings) | `translations.py` → `UI[lang][key]` | Looked up via `t(lang, key)`. English and Spanish entries must be kept in sync manually. |
| Workbook-sourced text (level names, dimension questions, solution value props) | `translations.py` → `_ES_LOOKUP` | `translate_fw(lang, text)` maps exact English strings to Spanish. A missing entry degrades to English rather than crashing. |

---

## 5. Assessment model (reference)

- **5 dimensions**, 1 maturity question each, scored **0–5** (0 = not assessed /
  excluded from results).
- The **radar chart** plots each dimension's score alongside the industry MVS benchmark.
- **Recommendations** pick the 3 lowest-scoring assessed dimensions, tie-broken by a
  fixed business priority order (Strategy > Operations > Connectivity > People >
  Intelligence). For each, up to 3 solutions are pulled from the workbook's catalog,
  topped up from fallbacks if the exact level has fewer entries.
- **Customer stories** are matched to the recommended dimensions by category and
  maturity-bucket, deduped by customer name across dimensions.
- The **PDF report** (built with `fpdf2`, no browser/Kaleido dependency) reproduces the
  radar, KPI table, and recommendations with hand-drawn vector primitives.

### Analytics columns (in order)

```
timestamp_iso, share_data, name, company, email, food_category,
motivation, investment_approach, language,
strategy_level, people_level, operations_level,
connectivity_level, intelligence_level, assessed_count
```

If the participant declines to share data (`share_data=False`), PII fields (name,
company, email, motivation, investment_approach) are blanked before writing — dimension
scores are still recorded so aggregate stats stay complete.

---

## 6. Project structure

```
app.py                  Main Streamlit app (screen flow, rendering, analytics)
data_loader.py          Parses the Excel workbook into dicts/lists
translations.py         UI strings, dimension names/icons, ES translations
pdf_report.py           PDF report generation (fpdf2)
requirements.txt        Python dependencies
Digital_readiness_tool_Framework.xlsx   Content workbook (source of truth)
Casos de éxito MX.xlsx  Customer success stories (Mexico)
fonts/                   Fonts for PDF generation
.streamlit/             Streamlit config & secrets template
```
