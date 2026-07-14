# At 10,000 Feet — Intelligent Automation Maturity Assessment

A single-page **Streamlit** app for **Foro MX 2026** participants to self-diagnose
their maturity in intelligent automation across **5 pillars** (18 questions). Users
enter their info, answer the questionnaire, and see a results screen with a normalized
radar chart, a per-pillar "equation" of scores, their overall level, and a personalized
recommendations roadmap. Every submission is logged to Google Sheets for forum analytics.

The UI is entirely in **English**.

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

**Local-dev analytics fallback:** if Google Sheets secrets are not configured, every
submission is appended to `./submissions_local.csv` and a warning is shown in the
sidebar. No setup is required to try the app locally.

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

## 4. Scoring model (reference)

- 5 pillars, 18 questions, each scored **0–3**. Pillar maxes: `12 / 12 / 12 / 12 / 6`;
  total max **54**.
- **Radar** normalizes each pillar to `raw / pillar_max * 100` so the 2-question pillar
  (Operational Control & CI) is comparable to the 4-question pillars.
- **Overall level** (0–5) comes from the total score against the `LEVELS` table.
- **Per-pillar level** uses proportional percentage cuts consistent with that table
  (`get_pillar_level`).

### Analytics columns (in order)

```
timestamp_iso, name, company, email, role,
q_data_1..4, q_infra_1..4, q_invest_1..4, q_change_1..4, q_opctrl_1..2,
data_raw, infra_raw, invest_raw, change_raw, opctrl_raw,
data_level, infra_level, invest_level, change_level, opctrl_level,
total, level_num, level_name
```

---

## 5. Notes / assumptions baked in

- **0–3 scale labels:** 0 = Not implemented · 1 = Early/partial · 2 = Mostly in place ·
  3 = Fully consolidated.
- Sliders that default to 0 can't distinguish "answered 0" from "untouched", so the
  questionnaire uses `st.radio` with no default selection — a question only counts as
  answered once the user clicks a value.
- FactoryOS **"partially"** actions are counted as accelerated (shown with an amber
  `Partial` badge); **"yes"** shows a green `Full` badge.
- "Remaining recommended actions" = the user's forward journey (current pillar level up
  to Level 5), not already-achieved steps.
- Internal `Source:` citations from the recommendations catalog are **not** displayed.
