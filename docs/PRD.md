# PO Exception Triage: Product Requirements Document

**By Muhammad Hamdan Ishfaq · Version 1.1 (final) · October 12, 2026**

## Changes in v1.1

This version folds in four reviewed critiques. Everything else is carried over from v1.0.

- **F1, F2, F13:** a planted-signal registry in the generator and a recovery test in the evaluation. History is extended to 36 months so every planted rule appears in the train, validation, and test windows.
- **F5, F6:** holding cost is now defined from the projected stock timeline. Every option shows inventory days added and peak cash tied up. Plant transfers get a donor-plant safety stock constraint.
- **F16:** the Power BI dashboard is promoted to P0, built on SQL views kept in the repo, and moved to Week 5.
- **F17, F18 (new):** a vendor message reader that turns unstructured emails into validated signals, a new pipeline entry node with two triggers, and a fourth demo story.
- **Sections 8 to 16:** UI, repo layout, milestones, risks, definition of done, and the launch storyboard are updated to match.

## 1. Summary

**One-liner:** An agentic exception-management system that finds purchase orders likely to arrive late (predicted by a model or reported by the vendor), checks whether the delay will actually cause a stock-out, quantifies the damage across MM and SD, ranks sourcing options by expected cost under hard business rules, and drafts the action for human approval.

**What it is:** A portfolio demo, not a product. It runs on mock data shaped like real SAP tables, plus one read-only connector to SAP's public sandbox. Total cost: $0.

**Why it exists:** To show hiring managers and senior SAP people one thing: you can turn a prediction into a governed business decision. Prediction alone is commoditized, and SAP itself now ships Joule agents for disruption handling, so this project does not pitch an autonomous resolver as innovation. The differentiators are domain correctness, guardrails, and measured evaluation. It demonstrates that you understand the problem.

**Positioning line for the post:** Most delay alerts are noise. I built a triage layer that asks the question an MM planner asks first: will this late PO actually cause a stock-out, and what is the cheapest safe fix?

**Honesty rule:** Everything is labeled mock or sandbox. No real company data, no ROI claims, no autonomous-in-production claims. Results on planted signals validate the pipeline, not real-world accuracy.

## 2. Goals and non-goals

**Goals**

1. A public demo link and a 60-second video that a recruiter understands in 10 seconds and a senior MM/SD consultant respects in 30.
2. Visible proof of four skills: SAP MM/SD process knowledge, applied ML with honest evaluation, agent engineering with guardrails, and analyst tooling (SQL and Power BI).
3. A repo that survives a skeptical engineer: tests, evals, data card, model card, limitations.
4. $0 build and hosting cost.

**Non-goals**

- No connection to any real SAP system and no writes to SAP.
- No fully autonomous purchasing. Level 3 auto-act is simulated within policy.
- No real FFC data, screenshots, or process specifics (NDA).
- No claims of real-world accuracy from synthetic data.
- No generic chatbot, multi-agent swarm, voice, or auth system.

## 3. Audiences and what each must see

- **Recruiters (non-technical):** a clear headline result, a clean 60-second video, a plain-English README top section, and role keywords (SAP MM/SD, supply chain analytics, applied AI).
- **Senior SAP MM/SD consultants:** correct tables and fields, MD04 and ME2N-style thinking, info records and source lists, release strategy logic, planned delivery time drift, and the MM-SD linkage.
- **AI engineers:** time-based validation, calibration, baselines, SHAP, planted-signal recovery, LLM grounding checks, prompt-injection tests on vendor names and email bodies, an eval harness, and reproducibility.
- **Supply chain managers and analysts:** cover days, OTIF, concentration risk, expected-cost and working-capital tradeoffs, what-if analysis, and a Power BI dashboard backed by SQL views.

## 4. Design principles

1. **Deterministic core, LLM at the edge.** Numbers, rankings, and constraints come from code. The LLM narrates, drafts, and extracts fields from untrusted text, and every output is validated by code before it is used.
2. **Impact before alerts.** A late PO matters only if it causes a stock-out or a service failure.
3. **Hard rules beat soft scores.** Blocked vendor, invalid source list entry, MOQ, donor-plant safety stock, and approval thresholds are constraints, never penalties.
4. **Human in the loop by default.** Autonomy is earned by policy.
5. **Every decision is explainable and auditable.**
6. **Honest data.** Synthetic data is declared and claims are scoped to what was tested.
7. **Free to build and run.**

## 5. The agent pipeline

Implemented as a LangGraph state graph with deterministic nodes and two LLM nodes (message extraction and narration):

1. **Signal intake:** two triggers feed the same pipeline. The predictive trigger is a model score on open schedule lines. The reactive trigger is a vendor message read by the extractor (F18) and validated in code.
2. **Ingest:** load open PO schedule lines and context from the mock SAP database.
3. **Score:** delay probability and expected delay days per schedule line (XGBoost). A validated vendor-reported delay overrides the model score for that line and carries its provenance.
4. **Project:** net inventory timeline per material-plant; compute cover, stock-out date, and gap.
5. **Filter:** escalate only if risk and gap thresholds are met.
6. **Assess impact:** shortfall, value at risk, and the open sales orders and customers affected (SD).
7. **Generate options:** expedite, alternative vendor (split), plant transfer, accept.
8. **Decide:** rank by expected cost under hard constraints (OR-Tools CP-SAT for split allocation), including holding cost and cash tied up.
9. **Narrate:** the LLM writes the explanation, vendor email, and internal note from the case file.
10. **Validate:** schema, numeric grounding, and constraint check; retry once, then fall back to a template.
11. **Gate:** apply the autonomy policy and route to approval or the queue.
12. **Emit:** on approval, produce a PO payload preview (never sent) and write the audit log.

## 6. Data model (mock, SAP-shaped)

Use real SAP table and field names so the schema itself demonstrates domain knowledge. Verify field names against your own FFC experience and one SAP reviewer before finalizing.

**Master data**

- MARA (MATNR, MTART, MATKL, MEINS): material
- MARC (MATNR, WERKS, DISMM, DISPO, BESKZ, PLIFZ planned delivery time, WEBAZ GR processing time, EISBE safety stock, MINBE reorder point): plant data
- MARD (MATNR, WERKS, LGORT, LABST unrestricted stock): storage location stock
- MBEW (MATNR, BWKEY, STPRS standard price, VERPR moving average price)
- MVER: consumption history by period
- LFA1 (LIFNR, NAME1, LAND1, SPERM purchasing block)
- T001W: plants
- KNA1 (KUNNR, NAME1) and KNVV (KUNNR, VKORG, KDGRP customer group, used as customer tier)

**Purchasing**

- EKKO (EBELN, BSART, LIFNR, BEDAT, EKORG, EKGRP, WAERS, ZTERM payment terms, FRGKE release indicator)
- EKPO (EBELN, EBELP, MATNR, WERKS, MENGE, NETPR, PEINH, ELIKZ, LOEKZ)
- EKET (EBELN, EBELP, ETENR, EINDT, MENGE, WEMNG): schedule lines
- EKES: vendor confirmations (EINDT, MENGE), including confirmation changes
- EKBE (VGABE, BEWTP, BUDAT, MENGE): PO history; goods receipts give actual delivery dates
- EINA (INFNR, MATNR, LIFNR) and EINE (INFNR, EKORG, WERKS, APLFZ, NETPR, MINBM, NORBM): info records
- EORD (MATNR, WERKS, LIFNR, VDATU, BDATU, FLIFN, NOTKZ): source list

**Demand and sales**

- RESB (BDTER, BDMNG, ENMNG): reservations
- VBAK (VBELN, KUNNR, AUDAT, VKORG, NETWR, WAERK), VBAP (VBELN, POSNR, MATNR, KWMENG, WERKS, NETWR), VBEP (VBELN, POSNR, EDATU, WMENG, BMENG)
- A derived MD04-style requirements view built from RESB, VBEP, open PO receipts, and a forecast table

**App tables (not SAP)**

predictions, case_files, options, decisions, audit_log, policy_config, eval_runs, vendor_messages (the simulated inbox), extracted_signals (validated extraction results with provenance), and planted_rules (generator ground truth, used only by evaluation).

**Generator specification**

- About 40 vendors, 300 materials, 3 plants, 36 months of history, about 20,000 PO lines, and 2,000 open sales order lines. History is 36 months so each planted rule appears in the train, validation, and test windows (suggested split: months 1 to 24 train, 25 to 30 validation, 31 to 36 test).
- Vendor archetypes: reliable, seasonal (for example Q4 congestion), drifting (getting worse over time), chronically late, and single-source critical.
- Lead times are lognormal per vendor-material with archetype-specific parameters. Confirmation changes (EKES) correlate with eventual lateness.
- Planted-signal registry: about five delay mechanisms with business rationale, applied probabilistically with label noise, and declared in rules.yaml (see F1).
- Seeded traps for evaluation: a blocked alternative vendor, an expired source list entry, an MOQ conflict, a missing info record, stale planned delivery times, and a vendor name field containing a prompt-injection string.
- A simulated vendor inbox of 30 to 40 synthetic emails with gold extractions, including ambiguous and adversarial cases (see F18).
- Fixed random seed. DATA_CARD.md documents every assumption.

## 7. Feature specifications

Priority key: **P0** must ship, **P1** should ship, **P2** stretch. Since time is available, the target is P0 and P1 complete, with P2 as time permits.

### F1. Mock SAP data generator (P0)

- Generates the schema above into SQLite (Postgres optional locally).
- Planted-signal registry (rules.yaml): about five mechanisms, each with a business rationale, applied probabilistically (never deterministically), with about 10% label noise and at least two decoy features that have zero true effect. Planted mechanisms:
    1. Seasonal vendor × Q4 × quantity above 2x the vendor's typical order.
    2. Two or more confirmation pushes with cumulative slip over 5 days.
    3. Open-PO load per vendor above a capacity proxy, with non-linear slippage.
    4. A drifting vendor whose lead time trends upward (tests drift features and the planned-versus-observed gap).
    5. Plant × material-group interaction (for example extra customs days at one plant).
- Each rule must be active in the train, validation, and test windows, with enough labeled lines in train (aim for several hundred per rule).
- The registry is ground truth for evaluation only. It is never exposed as a model feature. Noise is not tuned to reach an attractive metric.
- **Acceptance:** deterministic with seed; referential integrity checks pass; DATA_CARD.md lists assumptions, every planted rule, and row counts.

### F2. Delay risk model (P0)

- **Label:** late if the actual GR date (EKBE) exceeds the confirmed delivery date (EKES, else EKET) by more than a tolerance (default 1 day).
- **Features (all computed as of the snapshot date, no leakage):** vendor OTIF over trailing 90 and 180 days, vendor lead-time mean and variance, vendor-material history, quantity relative to vendor typical, PO age, open PO load per vendor, number and size of confirmation date changes, month, material group, planned versus observed lead-time gap.
- **Models:** an XGBoost classifier for P(late) and an XGBoost quantile regression for delay days (P50, P90).
- **Evaluation:** time-based split (train, validation, test by period), PR-AUC, Brier score, calibration curve and ECE, comparison against baselines (vendor mean lateness, logistic regression), and cost-based threshold selection.
- **Planted-signal recovery test, per rule:** (a) slice lift, comparing model performance where the rule is active versus inactive; (b) SHAP interaction values or partial dependence recovering the expected direction; (c) an ablation that removes the rule's inputs and measures the drop. Report "recovered k of N" exactly as measured.
- **Acceptance:** a model card with metrics, recovery results, and limitations. If XGBoost does not beat the baseline meaningfully, say so in the README.
- Weather is deliberately excluded: weak signal and hard to defend.
- Metrics on synthetic data validate the pipeline, not real-world performance. Recovery of planted rules is a pipeline sanity test, and the README says so.
- **Optional benchmark:** a notebook applying the same methodology to a public delivery dataset (Olist or DataCo), noting these are customer-delivery datasets, not inbound PO data.

### F3. Impact engine (P0)

- Builds a day-by-day projected stock for each material-plant: MARD stock, minus demand (RESB, VBEP, forecast), plus other open receipts.
- **Outputs:** cover days, projected stock-out date, gap days (delayed arrival minus stock-out), shortfall quantity, and safety stock breach flag.
- **Value at risk:** shortfall times unit value (MBEW) plus a configurable line-down or lost-margin cost.
- **Criticality:** ABC (consumption value) and XYZ (demand variability) classification.
- **Escalation rule:** escalate if P(late) is at or above a threshold AND (stock-out before arrival OR safety stock breach). Thresholds are configurable.
- **Acceptance:** the headline statistic is computed and shown (of N flagged POs, only M escalate). Unit tests cover zero demand, partial receipts, and multiple POs for one material.

### F4. SD impact view (P0)

- For each escalated case, list the open sales order lines (VBAK, VBAP, VBEP) that depend on the material in the gap window.
- Show customers affected, customer tier (KNVV-KDGRP), order value, promised dates (EDATU), confirmed quantities, and a penalty-risk flag.
- **Allocation suggestion:** which orders to protect first, using tier, value, and date priority. This is a simple rules-based ATP-style allocation, clearly labeled as a simplification.
- **Acceptance:** every escalated case shows revenue at risk and customers affected, and the allocation rules are documented.

### F5. Options engine (P0)

**Candidate actions:**

1. Expedite with the current vendor (cost premium, achievable date uncertain).
2. Split to an alternative vendor from info records (EINA/EINE) and valid source list entries (EORD).
3. Transfer stock from another plant (stock transport order with transfer lead time and cost).
4. Accept the delay (with safety stock use or customer communication).

**Hard constraints, never traded off:**

- Vendor not blocked (LFA1-SPERM).
- Source valid on the date (EORD).
- MOQ and standard order quantity respected (EINE).
- Lead time must beat the stock-out date to count as a fix.
- Approval thresholds.
- A single-source concentration cap.
- Donor-plant protection: for a plant transfer, the donor plant's projected stock must stay above its safety stock after the transfer. Otherwise the option is invalid, because it would create a second stock-out.

Split quantity allocation is solved with OR-Tools CP-SAT. **Acceptance:** zero hard-constraint violations across all eval scenarios.

### F6. Expected-cost decisioning (P0)

- Expected cost of an option = incremental purchase cost + freight or expedite fee + holding cost + P(option fails) × stock-out cost.
- Holding cost = the sum over days of (extra units on hand versus the baseline projection) × unit value (MBEW STPRS or VERPR) × annual carrying rate / 365. The extra units come straight from the F3 projected-stock timeline.
- The annual carrying rate is a configurable, labeled assumption, split into cost of capital and physical carrying cost (storage, obsolescence, insurance).
- **Working-capital metrics shown per option:** inventory days added and peak cash tied up.
- **Stated simplification:** payment terms (EKKO-ZTERM) decide whether earlier receipt pulls payment earlier. The demo shows gross cash tied up. A payment-terms offset is a P2 refinement.
- The arithmetic is shown transparently in the UI.
- **Acceptance:** a ranked list with a cost breakdown per option, working-capital metrics on every option, and near-ties flagged for human judgment.

### F7. What-if simulator (P0)

- Monte Carlo (5,000 runs) sampling lead time from the vendor distribution or quantile model, and demand with noise.
- Sliders: delay days, demand spike percent, safety stock, expedite success rate, alternative vendor reliability.
- Outputs: probability of stock-out by date, expected shortfall, P50 and P90 stock-out dates, and a side-by-side comparison of options.
- **Acceptance:** runs in under 3 seconds and is seeded for repeatable demos.

### F8. Master data drift detector (P0)

- For each material-plant-vendor, compare planned delivery time (MARC-PLIFZ, EINE-APLFZ) with observed lead time (PO date to first GR from EKBE): median, P80, and trend.
- Flag drift beyond configurable absolute and relative thresholds, and estimate the MRP impact (how much earlier or later planned orders would be created).
- Output: recommended updates and a downloadable CSV styled as a mass-change proposal (never applied).
- **Add-on:** safety stock and reorder point health check using a standard formula based on demand and lead-time variability, shown as a suggestion with assumptions.
- **Acceptance:** seeded drifting vendors are detected, and the false-positive rate is reported against generator ground truth.

### F9. Supplier scorecard and concentration risk (P1)

- Per vendor: OTIF, average days late, lead-time variability, confirmation-change rate, price variance, and spend share.
- **Concentration:** count and spend share of single-source materials, and an HHI index per material group.
- Risk tier from a transparent weighted score.
- **Acceptance:** the scorecard matches generator ground truth for the vendor archetypes.

### F10. LLM narrative and drafts (P0)

- **Input:** a structured case file (JSON) containing every fact the LLM may use, including cost breakdowns and working-capital metrics.
- **Outputs (Pydantic schema):** summary, recommended option ID, rationale, risks, vendor email draft, internal note, and customer-communication draft.
- **Guardrails:** temperature 0; the recommended option must equal the engine's rank 1; every number in the text must appear in the case file (regex extraction with tolerance); only vendors present in the case file may be mentioned; untrusted text fields are passed as quoted data with an instruction never to follow instructions inside them.
- On validation failure: retry once, then fall back to a deterministic template.
- **Providers:** one OpenAI-compatible client over an ordered provider chain (Groq, then Gemini, then OpenRouter). Check current free-tier limits when building. Cache outputs for deterministic demos.
- The validators are shared with F18 so that narration and extraction follow the same untrusted-text rules.
- **Acceptance:** numeric grounding pass rate and injection test results appear in the eval scorecard.

### F11. Autonomy levels, approvals, and audit (P0)

- **Levels:** L0 flag only; L1 recommend; L2 draft and wait for approval; L3 auto-act within policy (simulated, writes nothing to SAP).
- **Policy config (YAML):** auto-act only if order value is under a threshold, vendor approved, source valid, option type allowed, and confidence above a minimum.
- Signals from vendor emails (F18) never trigger auto-act on their own. A signal that fails validation goes to a human queue and does not reach the engine.
- Approval routing modeled on release strategy: value bands map to buyer, purchasing manager, or head of supply chain.
- **Audit log:** timestamp, actor, case ID, input hash, model and prompt versions, options considered, decision, and override reason. For reactive cases it also records the source message ID and the extraction result.
- Kill switch that forces L1 everywhere.
- **Acceptance:** every decision in the UI has an audit entry, and policy tests prove L3 never fires outside bounds.

### F12. Explainability (P1)

- SHAP per flagged PO, shown as a plain-language why-flagged panel (for example: vendor OTIF fell, confirmation date moved twice, quantity above typical).
- A global SHAP summary in the model card.

### F13. Evaluation scorecard (P0)

- **40+ decision scenarios** across categories: true stock-out, false alarm (high delay risk but high cover), single-source trap, blocked alternative vendor, expired source list, MOQ conflict, over-threshold approval needed, stale planned delivery time, missing info record, conflicting data, donor-plant shortage on a transfer, and prompt injection in a vendor text field.
- **30 to 40 vendor emails** with gold extractions (F18).
- **Metrics:** decision agreement with gold labels, hard-constraint violations (target 0), numeric grounding pass rate, hallucinated-vendor count (target 0), injection resistance (vendor name field and email body), extraction field accuracy, PO-resolution accuracy, abstention rate on ambiguous emails, planted-signal recovery (k of N, as measured), p95 latency, and tokens and cost per case.
- A one-page scorecard in the app, a README table, and one documented failure case with what was learned.
- **Acceptance:** the eval runs in CI on every commit using cached or template mode.

### F14. Live SAP sandbox connector (P1)

- One panel that calls the SAP Business Accelerator Hub sandbox (free API key) for purchase order data via the standard purchase order OData service, shown next to the mock-schema mapping.
- Clearly labeled: sandbox demo data, read-only.
- Handles failures gracefully (sandbox down or rate-limited) by showing cached sample responses.
- **Acceptance:** the API key lives in an environment variable and is never committed.

### F15. MCP server (P2)

- Read-only tools: `list_at_risk_pos`, `get_case_file`, `run_simulation`, `list_alternatives`, `draft_po_preview`.
- Lets any MCP client query the triage engine.
- State honestly in the README that SAP sandbox MCP servers already exist; the value here is the triage logic behind the tools.
- First cut if the schedule slips.

### F16. Companion Power BI dashboard (P0)

- Built in Power BI Desktop (free) on SQL views kept in the repo under /sql (OTIF, cover days, drift, concentration), reading the same mock data the app uses.
- **Scope:** one page with five visuals (OTIF trend, lead-time variance by vendor, cover days by material, concentration risk, drift summary) and value at risk as the headline number.
- Shared as screenshots and a short clip, since publishing may need a license.
- **Consistency test:** the Streamlit app and the dashboard export read the same views, and a test asserts the headline numbers match.
- **Rationale:** analyst job posts lead with SQL and Power BI far more often than agents. The dashboard opens the demo video and the SQL views show the query skills behind it. The README makes no claim about hiring outcomes.
- **Acceptance:** the dashboard exists, uses the repo's SQL views, and its headline numbers match the app.

### F17. Demo mode and scenario presets (P0)

Four guided stories with one-click loading:

1. **The false alarm:** 90 percent delay risk, but 35 days of cover, so no action. Shows the system's restraint.
2. **The real stock-out:** moderate risk, thin cover, three customers exposed; the best option is a split to an alternative vendor.
3. **The single-source trap:** no alternative exists; the best action is a plant transfer plus customer communication.
4. **The vendor email:** a vendor message reports a port-strike delay, the extractor pulls the PO and new date, validation passes, and the case moves into the impact engine with provenance shown.

**Acceptance:** a public Streamlit link with no login that loads in under 5 seconds.

### F18. Vendor message reader (P1)

**Purpose:** let the LLM read unstructured inbound text and bridge it to structured SAP data. In real SAP, vendor responses arrive through portals, EDI, or Business Network and land as confirmations (EKES). A simulated email inbox stands in for that channel in the demo, and the README says so.

- **Input:** a simulated inbox of 30 to 40 synthetic vendor emails, stored in vendor_messages.
- **LLM extraction into a Pydantic schema:** PO number(s), schedule line, new date or delay days, quantity affected, reason category, confidence, and an evidence span. This is text only. PDF or ASN extraction is out of scope (P2).
- **Deterministic resolution in code before anything reaches the engine:**
    - Relative dates (for example "two weeks") are resolved against the email date.
    - The PO must exist in EKKO/EKPO.
    - The sender must match the LFA1 vendor on that PO.
    - The date must be plausible (after the PO date and consistent with the schedule line).
    - Ambiguous or failing emails go to a human queue and never reach the engine.
- **Output:** an EKES-style vendor-reported confirmation, simulated and tagged with provenance `vendor_email`, stored in extracted_signals and fed to the Impact Engine (F3).
- **Guardrails:** the email body is untrusted data. The evidence span must be a literal substring of the email. The extractor has no tool access and writes nothing to SAP. Shared validators with F10.
- **Seeded cases:** multiple POs in one email, partial quantity, forwarded thread, relative dates, a PO number that does not exist, a sender that does not match the vendor, and an email containing an injection string.
- **Acceptance:** field accuracy, PO-resolution accuracy, abstention on ambiguous emails, and injection resistance are reported on the eval scorecard.

## 8. UI specification (Streamlit)

1. **Command Center:** KPI strip (open POs, flagged, escalated, value at risk, customers exposed), triage table sorted by value at risk, trigger source (model or vendor message), and filters.
2. **Case View:** risk and SHAP panel, projected stock timeline chart with stock-out marker, SD impact list, ranked options with cost breakdown plus inventory days added and cash tied up, narrative, autonomy status, and Approve / Reject / Override buttons.
3. **What-If Lab:** sliders and stock-out probability curves.
4. **Master Data Health:** drift table, mass-change CSV, and safety stock suggestions.
5. **Supplier Scorecard:** vendor ranking and concentration heatmap.
6. **Vendor Inbox:** simulated emails, extracted fields with evidence spans, validation result, and the human queue.
7. **Evaluation and Governance:** eval scorecard, planted-signal recovery, audit log, autonomy policy view, and kill switch.
8. **Live SAP Connector:** sandbox call panel.
9. **About:** data card, model card, limitations, and how this would run on real SAP.

**Style notes:** use SAP-user vocabulary (plant, schedule line, MRP controller, info record); show the SAP table behind each number in a small tooltip; keep it clean, not flashy.

## 9. Technical stack and cost

- **Language and libraries:** Python 3.12, pandas, SQLAlchemy, SQLite (Postgres via Docker optional), SQL views, XGBoost, scikit-learn, SHAP, OR-Tools, Pydantic, LangGraph, Plotly, Streamlit, pytest, ruff.
- **LLM:** Groq, Gemini, or OpenRouter free tiers, via one OpenAI-compatible client.
- **Hosting:** Streamlit Community Cloud; GitHub for the repo and Actions CI.
- **BI:** Power BI Desktop.
- **Total cost:** $0.

**Repo layout:** /data_gen (including rules.yaml and the synthetic inbox), /sap_schema, /sql, /models, /engine (impact, options, cost, simulate, drift, scorecard), /agent (graph, llm, extract, validators, policy), /app (Streamlit pages), /evals, /powerbi, /mcp_server, /docs (DATA_CARD, MODEL_CARD, ARCHITECTURE, LIMITATIONS), /tests.

## 10. Non-functional requirements

- **Reproducible:** one command builds the data, trains the models, and launches the app.
- **Tested:** unit tests on impact math, constraints, holding cost, and policy; CI runs the eval harness; a consistency test checks that the app and the dashboard headline numbers match.
- **Fast:** case view and simulator each under 3 seconds.
- **Secure:** no secrets in the repo; untrusted text (vendor names and email bodies) isolated from instructions; no real company data.
- **Documented:** README with a 10-second summary at the top, an architecture diagram, data card, model card, and limitations.

## 11. How this would run on real SAP (for the About page)

- **Data:** extract via CDS views, ODP, or OData instead of raw tables.
- **Vendor signals:** confirmations and delay notices arrive through Business Network, EDI, or portals and land in EKES, not through a mailbox.
- **Hosting and agents:** SAP BTP with Joule Studio or custom services; events through Event Mesh.
- **Actions:** PO changes through the purchase order OData API with proper authorization and release strategy.
- **Users:** results delivered into a Fiori worklist or inbox.
- This is out of scope for the demo, and the page says so openly. It shows you know the path without pretending you built it.

## 12. Risks and mitigations

- **Scope creep with lots of time:** freeze the P0 and P1 list now; anything else goes to a backlog file. If the schedule slips, cut F15, then F14.
- **Circular ML on synthetic data:** declare it, plant and recover documented signals, benchmark on a public dataset, report baselines, and never claim real-world accuracy.
- **Overclaiming recovery results:** report "recovered k of N" only as measured, and label it a pipeline sanity test.
- **Month-keyed rules unlearnable under a time split:** use 36 months or conditions that appear in every window.
- **LLM free-tier limits or outages:** cached outputs, provider failover, and template fallback.
- **Prompt injection through vendor names or email bodies:** untrusted text is data only, the extractor has no tools, evidence spans must be literal substrings, and injection tests are on the scorecard.
- **Domain errors exposed by seniors:** have one SAP person review the schema and logic before launch, and disclaim simplifications (ATP, MRP, payment-terms effect).
- **Looking like generic AI slop:** lead with the impact stat, show a failure case, and keep claims small.
- **Power BI scope growth:** one page, five visuals, built on repo SQL views.
- **NDA breach:** mock data only; review every screenshot.
- **Sandbox flakiness:** cached sample responses.

## 13. Milestones (about 9 weeks, with buffer)

- **Week 1 (Oct 12 to 18):** repo, schema, generator with planted-signal registry, and data card. Ask one SAP contact to sanity-check the schema.
- **Week 2 (Oct 19 to 25):** label definition, features, baselines, XGBoost, calibration, planted-signal recovery test, and model card.
- **Week 3 (Oct 26 to Nov 1):** impact engine, ABC/XYZ, escalation logic, and unit tests.
- **Week 4 (Nov 2 to 8):** SD impact view, options engine with donor-plant constraint, CP-SAT split, and expected-cost decisioning with holding cost.
- **Week 5 (Nov 9 to 15):** what-if simulator, drift detector, supplier scorecard, SQL views, and the Power BI dashboard.
- **Week 6 (Nov 16 to 22):** LangGraph pipeline with signal intake, LLM layer, validators, vendor message reader (F18), autonomy policy, approvals, and audit log.
- **Week 7 (Nov 23 to 29):** Streamlit app, demo mode, SHAP, and sandbox connector.
- **Week 8 (Nov 30 to Dec 6):** eval harness and scorecard, CI, and MCP server.
- **Week 9 (Dec 7 to 13):** README, docs, SAP-friend review, video, deploy, and post.
- **Target ship:** mid to late December 2026. Buffer weeks absorb FYP and internship load.

## 14. Definition of done

- The public demo link works without login and loads fast.
- All P0 and P1 features meet their acceptance criteria.
- The eval scorecard shows zero hard-constraint violations (including donor-plant protection) and zero hallucinated vendors.
- Planted-signal recovery is reported as measured, with the caveat that it validates the pipeline only.
- The Power BI dashboard and the Streamlit app show identical headline numbers, enforced by a test.
- Every option shows inventory days added and peak cash tied up.
- Extraction accuracy, abstention, and injection resistance for vendor emails are on the scorecard.
- README, data card, model card, and limitations are written.
- The 60-second video is recorded, and no real company data appears anywhere.
- At least one SAP professional and one engineer have reviewed it.

## 15. Launch plan

**Video storyboard (60 seconds)**

- **0 to 8s:** Power BI dashboard headline (value at risk, drifting vendors).
- **8 to 20s:** Streamlit triage table (for example, 31 flagged, only 7 will stock out) and the real stock-out case with the cover timeline and customers exposed.
- **20 to 32s:** a vendor email arrives, the extractor pulls the PO and new date, and the case updates.
- **32 to 42s:** drag the what-if slider and watch the stock-out probability move.
- **42 to 52s:** ranked options with expected cost, cash tied up, and the approval gate.
- **52 to 60s:** the eval scorecard and a mock-data, sandbox-connector tag.

**Post structure**

1. Hook: the problem in one line, then the result number.
2. Three bullets on what it does, with the MM/SD angle explicit.
3. One honest limitation line.
4. A question to seniors: MM and SD folks, which exception would you add?
5. A clear ask: graduating June 2027 and open to supply chain analytics and SAP plus AI roles in your target locations.

**Follow-up content over the next weeks**

- A post on the drift detector, aimed at MM consultants.
- A post on the failure case and what the eval taught you, aimed at AI engineers.
- A short write-up on why a late PO is not always a problem.
- A short write-up on the planted-signal recovery test and what it does and does not prove.

**Outreach and metrics**

Send the demo directly to 20 to 30 chosen SAP-shop supply chain and AI people with one tailored line each. Posts create impressions; targeted messages create conversations. No one can promise a flood of DMs, so track conversations and interviews rather than likes.

**Success metrics:** demo visits, profile views, real conversations, interviews booked, and referrals from SAP connections.

## 16. Assumptions and open questions

- Assumes you stay with Python and Streamlit and can use a free LLM tier.
- **To confirm:** free-tier quotas and terms at build time, Streamlit Community Cloud limits, and your target job locations (this decides which employers and keywords to emphasize).
- **To confirm:** have one senior SAP contact review field names and the simplified ATP and MRP logic before you publish.
- **To confirm:** the default annual carrying rate and its split, which are assumptions and are labeled as such in the app.
