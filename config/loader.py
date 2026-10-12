"""Load and validate every YAML in /config via pydantic (see schemas.py)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from config.schemas import Costs, Llm, Policy, Prereg, Thresholds

CONFIG_DIR = Path(__file__).resolve().parent


def _load(name: str, model: type[BaseModel]) -> BaseModel:
    with (CONFIG_DIR / name).open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return model.model_validate(data)


def load_thresholds() -> Thresholds:
    return _load("thresholds.yaml", Thresholds)  # type: ignore[return-value]


def load_costs() -> Costs:
    return _load("costs.yaml", Costs)  # type: ignore[return-value]


def load_policy() -> Policy:
    return _load("policy.yaml", Policy)  # type: ignore[return-value]


def load_llm() -> Llm:
    return _load("llm.yaml", Llm)  # type: ignore[return-value]


def load_prereg() -> Prereg:
    return _load("prereg.yaml", Prereg)  # type: ignore[return-value]


def validate_all() -> None:
    """Fail fast at startup if any config is invalid (called by engine/app entrypoints)."""
    for loader in (load_thresholds, load_costs, load_policy, load_llm, load_prereg):
        loader()