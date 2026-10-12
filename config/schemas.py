"""Pydantic models backing every /config/*.yaml file (M0: config validated at load).

Every loader raises validation errors at startup rather than letting bad config
propagate mid-run. Field names match the YAML keys 1:1.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SnapshotH(BaseModel):
    base: int
    min: int
    max: int


class NearTie(BaseModel):
    pct: float
    abs_usd: float


class Drift(BaseModel):
    min_obs_periods: int
    abs_days: int
    rel_pct: float


class XyzCutoffs(BaseModel):
    x: float
    y: float


class ScorecardWeights(BaseModel):
    otif: float
    lateness: float
    lt_variability: float
    confirmation_changes: float
    spend_share: float


class Thresholds(BaseModel):
    tolerance_days: int
    snapshot_h: SnapshotH
    projection_horizon_days: int
    arrival_basis: str
    escalation_threshold_mode: Literal["cost_based"]
    near_tie: NearTie
    drift: Drift
    target_service_level: float
    abc_cutoffs: list[float]
    xyz_cutoffs: XyzCutoffs
    scorecard_weights: ScorecardWeights
    extract_min_confidence: float
    email_length_cap: int
    mc_runs: int


class CarryingSplit(BaseModel):
    capital: float
    physical: float


class PenaltyPct(BaseModel):
    top_tier: float
    other: float


class ExpediteSuccess(BaseModel):
    reliable: float
    seasonal: float
    single_source: float
    drifting: float
    chronically_late: float


class Transfer(BaseModel):
    reliability: float
    lead_time_days: int
    cost_pct: float


class ThresholdCostMatrix(BaseModel):
    c_false_negative: float
    c_false_positive: float


class Costs(BaseModel):
    currency: Literal["USD"]
    annual_carrying_rate: float
    carrying_split: CarryingSplit
    line_down_cost_per_day: dict[str, float]
    penalty_pct: PenaltyPct
    expedite_fee_pct: float
    expedite_success: ExpediteSuccess
    transfer: Transfer
    order_fixed_cost: float
    threshold_cost_matrix: ThresholdCostMatrix
    max_vendor_share_pct: float
    max_split_vendors: int


class ApprovalBand(BaseModel):
    upto: float | None
    approver: str


class L3Policy(BaseModel):
    max_order_value: float
    min_confidence: float
    allowed_option_types: list[str]
    require_vendor_approved: bool
    require_source_valid: bool
    require_trigger: str


class Policy(BaseModel):
    kill_switch: bool
    default_level: Literal["L2"]
    l3: L3Policy
    approval_bands: list[ApprovalBand]


class RateLimit(BaseModel):
    tokens_per_sec: int
    burst: int


class Provider(BaseModel):
    name: str
    base_url: str
    model: str
    key_env: str


class PromptVersions(BaseModel):
    narrate: str
    extract: str


class Llm(BaseModel):
    mode: Literal["live", "replay", "template"]
    temperature: float = Field(ge=0, le=1)
    providers: list[Provider]
    rate_limit: RateLimit
    attempts: int
    cache_path: str
    prompt_versions: PromptVersions


class LabelH(BaseModel):
    base: int
    min: int
    max: int


class LabelPrereg(BaseModel):
    snapshot_h: LabelH
    tolerance_days: int


class Recovery(BaseModel):
    slice_lift_margin: float
    ablation_drop_margin: float
    seeds: int


class Baseline(BaseModel):
    require_beat_margin: float


class Prereg(BaseModel):
    label: LabelPrereg
    recovery: Recovery
    baseline: Baseline
    committed: str