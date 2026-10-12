# PO Exception Triage: Design Decisions Log

**Author:** Muhammad Hamdan Ishfaq
**Companion to:** `docs/PRD.md` v1.1, `docs/TRD.md` v1.0
**Purpose:** Records decisions taken after the first review of the PRD and TRD. Where a decision changes the TRD, the corresponding TRD edit is listed at the bottom.

## 1. Technology choices

### 1.1 Dataframes — pandas

Use **pandas**. The dataset is about 20k PO lines, so polars' speed advantage does not matter, and pandas integrates most smoothly with XGBoost, SHAP, scikit-learn, SQLAlchemy, and Streamlit. Skip DuckDB and pyarrow.

### 1.2 LLM providers — Groq first, then Gemini, then OpenRouter (no Ollama)

- Build one **`OpenAICompatClient`** that works with all three providers, because each exposes an OpenAI-style chat endpoint. Only the base URL, key, and model ID differ.
- `llm.yaml` holds an **ordered provider chain**. The client moves to the next provider on a 429, a 5xx, or a timeout, and skips any provider whose key is missing.
- Keep `ReplayClient` and `TemplateClient` as in the TRD. **Drop** `GeminiClient`, `GroqClient`, and `OllamaClient` as separate classes.
- **Skip LiteLLM.** It is a large dependency for about 60 lines of code, and the TRD stresses pinned, reviewed dependencies.
- **Remove `model_id` from the replay cache key.** Store the producing model inside each cache entry instead. Otherwise a failover to another provider misses the cache.
- Record the model on every eval run, and do not mix live runs from different providers into one headline number.
- Keep the Pydantic validate, retry once, then template flow as the real safety net. JSON-mode support varies by provider, especially on OpenRouter's free models.
- Use one account per provider rather than several accounts on one provider, which usually breaks free-tier terms.
- The public demo and CI run in **replay** mode, so keys are only needed locally when refreshing the cache.
- **Open question:** which keys exist. Aim for at least Groq plus one other before Week 6.

### 1.3 Machine setup (Windows)

- **Python:** 3.14.3 is installed, but a venv inherits the interpreter that created it, so the venv does not fix the version. Install 3.12 alongside it with `winget install Python.Python.3.12`, then run `py -3.12 -m venv .venv`. Add a `requires-python = "==3.12.*"` pin.
- **Ollama:** not installed and not needed. Removed from the TRD.
- **Power BI Desktop:** Windows-only and free from the Microsoft Store. Confirm it is installed, since the F16 timeline assumes it. No plan B needed.
- **Make:** `make` is not on Windows by default. Use a **`tasks.py` runner** (`python tasks.py data`), which behaves the same locally and in Linux CI.

### 1.4 Currency — USD

Use **USD** everywhere. It is easiest for the recruiter and SAP audience to read, and the TRD's example thresholds (L3 limit of 5,000, approval bands) stay at sensible magnitudes. Set `WAERS='USD'` everywhere and label it "single currency, USD".

## 2. Data and model design

### 2.1 Snapshot date — last day of history

- History spans **2023-10-01 to 2026-09-30**, with a **snapshot of 2026-09-30**.
- Open lines, including past-due ones, have no labels. They form the live queue and are excluded from training.
- End the labeled test rows about **30 days before the snapshot**. Late lines near the end have not arrived yet, so only on-time ones would look closed.
- Optionally keep the true future outcomes of open lines in an **eval-only table**, to check whether flagged stock-outs would have happened.
- **Amend R1.** With a 24/6/6 split, Q4 can fall in only one of the validation and test windows, so R1 as written fails TR-DATA-3. Give each seasonal vendor its own **`peak_quarter`** and change the condition to `quarter == vendor.peak_quarter`.
  - Roughly **8 to 10 seasonal vendors** and a heavy-tailed quantity distribution are needed to reach 100 R1 lines each in validation and test.
  - Run the **TR-DATA-3 population guard early in Week 1**, since R2 and R5 can fail the same way.

### 2.2 MVER period — monthly

Monthly matches SAP's period-based MVER. Use `daily_forecast = mean(last 6 months) / actual days in each month`. The TRD's one-row-per-period layout simplifies MVER's real GSV01 to GSV12 columns, so flag it to the SAP reviewer.

### 2.3 Vendor capacity — three distinct notions

Raw quantity mixes units of measure, so measure load in open lines or open value.

- **Generator (latent, never a feature):** `capacity_v = factor × vendor's long-run average open load`, with the factor around 1.2 to 1.5 and varied by archetype. Rule R3 fires when current load exceeds it.
- **Model feature:** only observable load against the trailing mean.
- **CP-SAT `cap_vm` (mock, labeled in the UI):** 1.5 × the P90 of that vendor's historical order quantity for the material. If there is no history, use the P90 across all vendors for that material.

### 2.4 Cost assumptions — placeholder defaults, tuned so different options win

If one option always wins, the eval suite proves nothing. Starting values in USD:

| Parameter | Value |
|---|---|
| Line-down cost per day | A = 2,000, B = 500, C = 100 |
| Penalty cost | 2% of line value for top tier, 0.5% for others |
| Expedite fee | 10% of line value |
| Expedite success by archetype | reliable 0.85, seasonal 0.70, single-source 0.75, drifting 0.60, chronically late 0.40 |
| Transfer reliability | 0.98, with 3-day lead time and cost of 2% of value |
| Order fixed cost | 50 |
| C_FN : C_FP | about 5 to 10 : 1 |

Make sure the 40-scenario suite has at least one case where each option type wins: expedite, split, transfer, and accept.

## 3. Cross-document reconciliation

- **11. Follow the TRD graph.** Put a PRD-step to TRD-node mapping table in `ARCHITECTURE.md`, and state the precedence rule: the PRD governs scope and priority, the TRD governs implementation.
- **12. The TRD is authoritative for `rules.yaml`**, with the R1 amendment above.
- **13. Fix `h` and tolerance now.**
  - Set `h=14` and `tolerance=1` in `thresholds.yaml` today. Changing either changes the label, so PR-AUC across settings is not comparable.
  - Commit a **`prereg.yaml`** before the first test run. It holds these values, the recovery margins (TR-ML-3), and the baseline-margin rule (TR-ML-2).
  - **Train/serve mismatch:** training at exactly 14 days before due does not match scoring open lines at arbitrary distances from their due date. Draw `h` per line from **[7, 28]** with a seeded generator, and add **`days_to_due`** as a feature. Decide this before writing `labels.py`.

## 4. Scope

- **14. Confirmed.** F15 (MCP server), PDF/ASN extraction, and the payment-terms offset are deferred entirely. Leave `/mcp_server` out or as a README stub. The cut order stays F15, then F14.
- **15. Do not write into the committed DB. Use three files.**
  - **`po_triage.db`:** a build artifact opened read-only, holding the SAP tables, views, predictions, case files, options, and extracted signals.
  - **A runtime state DB:** holds `decisions`, `audit_log`, and `policy_config` (including the kill switch). It is created from schema at startup, seeded with the precomputed baseline entries, and keeps the append-only triggers and hash chain.
  - **`eval_truth.db`:** holds `planted_rules` and the vendor message gold (`vendor_message_gold`; `po_triage.db` keeps the message bodies only). The app and engine never open it, so TR-DATA-1 becomes a structural guarantee instead of a grep test.
  - On Streamlit Community Cloud the filesystem is ephemeral and shared by all visitors, so one person's Approve or kill-switch click would show for everyone and vanish on reboot. For the public demo, use a **per-session state DB** (in-memory or a temp file keyed to the session) so each visitor starts clean. Locally it can be a persistent file.

## 5. TRD edits this implies (applied)

- **2.3 and 7.3:** replace the provider clients and Ollama with `OpenAICompatClient` and the chain config, and drop `model_id` from the cache key.
- **2.4, environment variables, Appendix C:** remove Ollama, and add `OPENROUTER_API_KEY`.
- **3 and Makefile references:** `tasks.py` instead of `make`.
- **4.1 and 4.2, TR-DATA-2:** split the tables across the three DB files.
- **4.3.1:** the R1 amendment (`peak_quarter`).
- **5.1 and 5.2:** per-line `h` and the `days_to_due` feature.
- Also applied for consistency: Dataframes set to pandas (2.3); snapshot date and history range recorded (4.3); the two vendor-capacity definitions noted (6.4); the USD cost defaults and per-line h added to Appendix A; and the stale Ollama/provider references in `docs/PRD.md` (F10 and the technical-stack list) updated to the Groq/Gemini/OpenRouter chain and pandas.
