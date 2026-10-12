# PO Exception Triage: Module-wise Implementation Plan

**Author:** Muhammad Hamdan Ishfaq
**Companion to:** `docs/PRD.md` v1.1, `docs/TRD.md` v1.0
**Date:** October 13, 2026

## 1. Purpose and precedence

This plan turns the TRD's module layout into a build order with gates. The PRD governs scope and priority. The TRD governs implementation. Where this plan and the TRD differ, the list of TRD edits in Section 6 says which TRD sections to update.

**Decisions already settled and applied here:**

- pandas for dataframes, Python 3.12 in a venv created with `py -3.12 -m venv .venv`, Windows with a `tasks.py` runner instead of make.
- USD as the single currency.
- Demo snapshot date 2026-09-30, with history from 2023-10-01 to 2026-09-30.
- Monthly MVER periods.
- Three database files: `po_triage.db` (read-only build artifact), a runtime state DB (decisions, audit log, policy config), and `eval_truth.db` (planted rules, gold emails).
- One `OpenAICompatClient` with a provider chain (Groq, then Gemini, then OpenRouter), plus `ReplayClient` and `TemplateClient`. No Ollama.
- Per-line snapshot horizon h drawn from [7, 28] with a seeded generator, and `days_to_due` as a feature.
- R1 amended to `quarter == vendor.peak_quarter`.
- P2 items (MCP server, PDF/ASN extraction, payment-terms offset) deferred. Cut order if the schedule slips: F15, then F14.

## 2. Dependency order

Build in this order, because each module depends only on the ones before it.

```
foundation -> sap_schema -> data_gen -> sql views -> models
                                    \-> engine (projection -> sd_impact -> options/cpsat/cost -> simulate, drift, scorecard)
models + engine -> agent (llm, validators, extract, narrate, policy, audit, graph)
agent + engine + models -> app -> evals -> docs and launch
sql views -> powerbi
```

**One change to the PRD schedule:** the SQL views move to Week 2 with the model. `vw_line_actuals` is the source for labels and OTIF features, and the TR-SQL-1 pandas cross-check doubles as a correctness test for both. Week 5 keeps only the BI export and the Power BI report.

## 3. Modules

### M0. Foundation (Week 1, days 1 to 2)

- **Build:** Python 3.12 venv, lock file, `.python-version`, `tasks.py` with targets `data`, `train`, `precompute`, `eval`, `app`, `bi-export`, `all`. `/config/*.yaml` validated with Pydantic. ruff, pytest skeleton, import-linter rules from TRD Section 3, pre-commit hook (secret patterns, plus a banned-terms list kept outside the repo), CI workflow stub.
- **Commit now:** `thresholds.yaml` with h range [7, 28] and tolerance 1 day, and `prereg.yaml`.
- **Done when:** CI runs lint and an empty test suite green, and a deliberately illegal import (engine importing agent) fails the import-linter test.

### M1. sap_schema (Week 1)

- **Build:** DDL split across the three DB files. The state DB holds `decisions`, `audit_log` and `policy_config` with the append-only triggers. `eval_truth.db` holds `planted_rules` and gold emails. Also `field_map.yaml` (SAP field to description, used for tooltips) and `integrity.py` (TRD Section 4.3.3 checks).
- **Done when:** the schema builds from nothing, and the audit triggers reject UPDATE and DELETE in a test.
- **Parallel task:** send the field list to your SAP contact now, including `EKES.ERDAT`, `EKES.EBTYP` and the MVER simplification.

### M2. data_gen (Week 1, the riskiest module)

Build in the TRD's stage order, one stage per commit, each on its own `SeedSequence.spawn` stream:

1. Plants, vendors (with archetypes and `peak_quarter` for seasonal ones), customers, materials.
2. MARC and MBEW, with stale PLIFZ for a subset.
3. EINA, EINE and EORD with the six seeded traps.
4. MVER (monthly) and FORECAST.
5. PO history over 36 months, then lead times, delays and planted rules (R1 amended, R2 to R5, 10% label noise, decoys).
6. EKES confirmation pushes, EKBE receipts, partial receipts.
7. Open lines (including past-due), RESB, sales orders, MARD stock calibrated for a wide cover-days range.
8. Email inbox with gold extractions.

- **Do first:** the TR-DATA-3 rule-population guard (300 train, 100 validation, 100 test lines per rule). Run it as soon as stage 5 exists, not at the end. R1 and R5 are the likeliest to fail. For R1 you will probably need 8 to 10 seasonal vendors and a heavy-tailed quantity distribution.
- **Also write:** an eval-only table of true outcomes for open lines.
- **Vendor capacity:** latent `capacity_v` is a factor of 1.2 to 1.5 times the vendor's long-run average open load, measured in open lines or open value, never raw quantity. It is never a model feature.
- **Done when:** the same seed gives an identical data hash, integrity checks pass, traps are findable by SQL, and `DATA_CARD.md` is generated.

### M3. sql views (Week 2)

- **Build:** the views in TRD Section 4.4, plus `vw_open_schedule_lines`, `vw_requirements_md04`, `vw_material_cover`, `vw_observed_lead_time` and `vw_vendor_concentration`.
- **Tests:** TR-SQL-1, comparing each view with a pandas recomputation on seed 42.
- **Done when:** all views pass the cross-check. `bi_export.sql` waits for M11.

### M4. models (Week 2)

Order: `labels.py`, `features.py`, baselines, `train.py`, `calibrate.py`, quantile models, `recovery.py`, `explain.py`, model card generator.

- **labels.py:** per-line h from [7, 28], the snapshot rule, `full_gr_date` at 95% of quantity, embargo logic, and labeled test rows ending 30 days before the final snapshot. Open lines have no labels and are excluded from training.
- **features.py:** as-of rules from TRD Section 5.2, with `days_to_due` added. Write the TR-ML-1 truncated-database leakage test the same day.
- **recovery.py:** per-rule slice lift, direction check and 5-seed ablation, using margins from `prereg.yaml`. Commit those margins before the first test-window run.
- **explain.py:** TreeSHAP, top 5 contributions to `shap_json`, and the plain-language dictionary.
- **Done when:** the model card shows metrics, calibration, baselines and "recovered k of N" as measured. If XGBoost does not beat the baseline, write that into the README draft immediately.

### M5. engine: projection and impact (Week 3)

- **Build:** the day-by-day projection, cover days, gap days, shortfall, safety breach, value at risk, ABC and XYZ classes, the single filter function behind the "N flagged, M escalate" statistic, and the overdue-line rule.
- **Tests:** all TR-ENG-1 cases, plus the invariants (receipts never lower stock, `gap_days >= 0`) as Hypothesis tests.
- **Done when:** the headline statistic comes from the pipeline's own filter, never computed separately.

### M6. engine: sd_impact (Week 4)

- **Build:** affected sales-order query, KNVV tier join, revenue at risk, greedy ATP-style allocation, `penalty_risk` flag.
- **Done when:** every escalated case returns revenue at risk and customers affected, and the allocation rules are printed for the docs.

### M7. engine: options, cpsat_split, cost (Week 4)

Build in this order, because each depends on the one before:

1. **options.py:** the four option generators and constraint checks C1 to C8, with `feasible` and `violated_constraints`.
2. **cpsat_split.py:** one worker, fixed seed, 2-second limit, and "infeasible, never a silent heuristic" behavior. `cap_vm` is 1.5 times the P90 of that vendor's historical order quantity for the material, falling back to the P90 across all vendors.
3. **cost.py:** expected-cost components, holding cost from the projected timeline, peak cash, inventory days added, near-tie logic, and the `cost_json` breakdown.

- **Tuning:** set `costs.yaml` so each option type wins in some scenario, and check this before writing the eval suite.
- **Tests:** a Hypothesis test that no ranked option violates C1 to C8, CP-SAT tests for MOQ, rounding and concentration, and cost-sum tests.
- **Done when:** the donor-plant shortage case produces an invalid transfer that never appears in the ranking.

### M8. engine: simulate, drift, scorecard (Week 5)

- **simulate.py:** vectorized and seeded, lognormal fit from (q50, q90), zero-inflated handling, five sliders. Add a perf test against the 3-second budget on your own machine early.
- **drift.py:** median, P80, Theil-Sen slope, flags, MRP impact, mass-change CSV with the "PROPOSAL ONLY, NOT APPLIED" header, and the safety stock check. Report precision and recall against the drifting vendors.
- **scorecard.py:** per-vendor metrics, weighted risk score, HHI, and the archetype rank-correlation test.

### M9. agent (Week 6)

Build in this order so each piece is testable alone:

1. **llm/:** `OpenAICompatClient` with the provider chain, token-bucket limiter, backoff, `ReplayClient` (cache key without model ID, producing model stored in the entry), `TemplateClient`, and metering.
2. **validators.py:** schema, option check, numeric grounding, vendor allow-list, constraint re-check, content rules. Write the unit tests first, because this is where most subtle bugs sit.
3. **narrate.py:** prompt v1, case-file builder with untrusted markers, retry once, template fallback, `narrative_path`.
4. **extract.py (F18):** preprocess, extraction prompt, checks V1 to V8, date resolution in code, queue or accept.
5. **policy.py:** `decide_level`, approval bands, kill switch, and the TR-POL-1 property test.
6. **audit.py:** hash chain and event types, writing to the state DB.
7. **graph.py and state.py:** LangGraph nodes, conditional edges, and `emit` in a single transaction. Include `payload.py` (PO preview).
8. **intake.py:** the predictive and reactive triggers.
9. **Batch precompute:** runs the graph for all candidate lines and fills the cache.

- **Done when:** a test fails the build if any `/agent` module imports a write-capable HTTP client, and injection strings in vendor names and email bodies are handled.

### M10. app (Week 7)

- **Build order:** `data_access.py` (read-only, the only place with SQL), Command Center, Case View with components (timeline chart, options table, SD table, tooltips), Vendor Inbox, What-If Lab, Master Data Health, Supplier Scorecard, Evaluation and Governance, About, demo presets.
- **State:** a per-session state DB held through `st.session_state`, so each visitor starts clean.
- **Done when:** the four presets load from cache in under 5 seconds with no keys and no network, and no page shows a raw traceback.

### M11. powerbi and BI export (Week 5)

- **Build:** `bi_export.sql`, CSV export through `tasks.py bi-export`, the star schema, the three DAX measures, and one page with five visuals and the value-at-risk card.
- **Test:** TR-BI-1, asserting that the app's data-access function equals the export view for value at risk, flagged count and escalated count.
- **Deliver:** screenshots and a short clip. Review every screenshot before publishing.

### M12. SAP connector (Week 7, P1)

- **First:** verify entity and property names in the API Business Hub explorer before coding the mapping.
- **Build:** a GET-only client with the `APIKey` header from an environment variable, 5-second timeout, one retry, fallback to `sandbox_sample.json`, and the mapping panel.
- **Done when:** the cache fallback test and the CI secret scan pass.

### M13. evals (Week 8)

- **Build order:** scenario YAML schema, `runner.py` (replay and template modes), 40 or more scenarios covering every listed category with at least one winner per option type, 30 or more emails with seeded ambiguity and injection cases, `report.py` (scorecard and failure-case writer), `check_gates.py`, CI integration.
- **Process rule:** write gold labels from each scenario's business logic, not from what the engine outputs.
- **Done when:** the CI gate fails on any hard-constraint violation or hallucinated vendor, and the replay suite runs in under 10 minutes.

### M14. Docs, review, launch (Week 9)

- **Build:** README (10-second summary first, honesty rules), architecture diagram, PRD-step to TRD-node mapping with the precedence rule, `LIMITATIONS.md`, final data and model cards, the About page, and "how this runs on real SAP".
- **Review:** one SAP professional on schema and logic, one engineer on code.
- **Launch:** record the video per the storyboard, deploy, post.

## 4. Calendar and gates

| Week | Modules | Gate to pass before moving on |
| --- | --- | --- |
| 1 | M0, M1, M2 | Rule-population guard passes, deterministic data hash |
| 2 | M3, M4 | Leakage test passes, recovery margins committed before the test run |
| 3 | M5 | All TR-ENG-1 tests green |
| 4 | M6, M7 | Zero constraint violations in the property test |
| 5 | M8, M11 | Perf under budget, app and BI numbers match |
| 6 | M9 | Validator and policy property tests pass, injection suite passes |
| 7 | M10, M12 | Presets load under 5 s offline |
| 8 | M13 | CI gates green in replay mode |
| 9 | M14 | Reviews done, video recorded |

## 5. Risk points

- **Week 5 is the heaviest.** With the views moved earlier it is manageable. If it slips, cut the safety-stock health check (an add-on in F8) before touching the simulator or BI.
- **Week 6 is the second heaviest**, with a graph, LLM layer, extraction and policy in one week. Start the `llm/` client and validators during Week 5 evenings, since they only need the case-file schema from M7.
- **Do not start the app early.** Case View depends on cost breakdowns and narration, so building it before M7 and M9 means rework.
- **Data generation can eat the whole schedule.** If the rule-population guard still fails after reasonable tuning in Week 1, simplify the rule condition rather than inflating the dataset.

## 6. TRD edits this plan implies

- Sections 2.3 and 7.3: replace the three provider clients and Ollama with `OpenAICompatClient` and the chain config, and drop `model_id` from the cache key.
- Section 2.4, environment variables, Appendix C: remove Ollama and add `OPENROUTER_API_KEY`.
- Section 3 and Makefile references: use `tasks.py` instead of make.
- Section 4.2 and TR-DATA-1, TR-DATA-2: split the tables across the three DB files.
- Section 4.3.1: the R1 amendment (`peak_quarter`).
- Section 5.1: per-line h and the `days_to_due` feature.
- Section 5.1: labeled test rows end 30 days before the snapshot.