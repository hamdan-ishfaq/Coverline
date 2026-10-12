"""Build runner for the repo. Keeps everything cross-platform (no make on Windows).

Targets (see PLAN M0 and TRD TR-ARCH-3):
  lint        ruff check .
  test        pytest across tests/{unit,property,integration,perf}
  data        generate + build the po_triage.db artifact (M2)
  train       fit + commit models, then precompute projections (M4/M5)
  precompute  precompute projections, signals, sd_impact for ingest (M5/M9)
  eval        run the eval suite in LLM mode and check gates (M13)
  bi-export   write bi_export.sql + extract the CSV used by Power BI (M11)
  app         launch the Streamlit app: streamlit run app/Home.py
  all         run the full build as CI/pipeline does
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_MISSING = (
    "{target} is not wired up yet; it lands in {milestone}. Nothing to do for now."
)


def _run(argv: list[str]) -> int:
    return subprocess.run([sys.executable, *argv], cwd=ROOT).returncode


def lint(_: argparse.Namespace) -> int:
    return _run(["-m", "ruff", "check", "."])


def test(args: argparse.Namespace) -> int:
    paths = []
    for rel in ("unit", "property", "integration", "perf"):
        d = ROOT / "tests" / rel
        if d.is_dir() and any(d.iterdir()):
            paths.append(str(d))
    # tests/unit always runs; the rest join as their dirs fill up.
    if not paths:
        paths = ["tests"]
    return _run(["-m", "pytest", "-q", *paths])


def data(args: argparse.Namespace) -> int:
    print(_MISSING.format(target="data", milestone="M2"), file=sys.stderr)
    return 1


def train(args: argparse.Namespace) -> int:
    print(_MISSING.format(target="train", milestone="M4"), file=sys.stderr)
    return 1


def precompute(args: argparse.Namespace) -> int:
    print(_MISSING.format(target="precompute", milestone="M5"), file=sys.stderr)
    return 1


def eval_(args: argparse.Namespace) -> int:
    print(_MISSING.format(target="eval", milestone="M13"), file=sys.stderr)
    return 1


def bi_export(args: argparse.Namespace) -> int:
    print(_MISSING.format(target="bi-export", milestone="M11"), file=sys.stderr)
    return 1


def app(args: argparse.Namespace) -> int:
    return _run(["-m", "streamlit", "run", str(ROOT / "app" / "Home.py")])


def all_(args: argparse.Namespace) -> int:
    _fns = {
        "lint": lint,
        "test": test,
        "data": data,
        "train": train,
        "precompute": precompute,
        "eval": eval_,
        "bi-export": bi_export,
    }
    for name in PIPELINE:
        print(f"[tasks] -> {name}")
        rc = _fns[name](args)
        if rc != 0:
            print(f"[tasks] {name} failed with {rc}", file=sys.stderr)
            return rc
    print("[tasks] all steps passed; launch the app with: python tasks.py app")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tasks.py")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for data/eval")
    parser.add_argument("--size", choices=["small", "full"], default="small")
    parser.add_argument("--mode", choices=["live", "replay", "template"], default="replay")
    sub = parser.add_subparsers(dest="target", required=True)
    for name, fn, help_ in (
        ("lint", lint, "ruff check ."),
        ("test", test, "run the pytest suite"),
        ("data", data, "generate + build po_triage.db (M2)"),
        ("train", train, "fit models and precompute projections (M4/M5)"),
        ("precompute", precompute, "precompute signals/sd_impact (M5/M9)"),
        ("eval", eval_, "run the eval suite and gates (M13)"),
        ("bi-export", bi_export, "emit bi_export.sql + BI CSV (M11)"),
        ("app", app, "streamlit run app/Home.py"),
        ("all", all_, "run the full pipeline in order"),
    ):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
    return parser


PIPELINE = ["lint", "test", "data", "train", "precompute", "eval", "bi-export"]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())