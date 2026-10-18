"""Does the finite-epsilon result survive higher dimension when the L2 bound stays fixed?

The ``d=4`` circuit constrains ``q_clip in {-1,0,1}^d`` with ``sum(q_clip^2) <= C_q^2 = 4``.
If that *same* bound is kept in dimension ``d >= 4``, every admissible update has at most
four non-zero coordinates, so two replacement-adjacent updates ``f(D), f(D')`` can differ in
at most eight coordinates. Writing ``a`` for coordinates where both are non-zero with
opposite sign (displacement 2) and ``b`` for coordinates where exactly one is non-zero
(displacement 1), feasibility is ``a <= 4`` and ``2a + b <= 8``. Coordinates where the two
updates agree leak nothing, whatever ``d`` is. Each round therefore composes ``a`` shift-2
and ``b`` shift-1 scalar privacy-loss distributions, and the worst case over feasible
``(a, b)`` is a dimension-free upper bound for the fixed-bound mechanism.

The earlier extrapolation in ``actual_multiround_halo2/privacy_boundary.py`` instead
assumed that *every* coordinate may move by 2 (``C_q^2 = d``); that envelope is reproduced
here as the second table so the two assumptions sit side by side.

Everything here is for the ideal sampler and fixed, non-adaptive displacement patterns,
exactly like ``centered_binomial_accountant.py``; it is not a transcript-level theorem.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

EXPERIMENTS_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_ROOT))

from discrete_noise_accounting.centered_binomial_accountant import (  # noqa: E402
    ComposedPrivacyProfile,
    field_low_bit_bias_bound,
    scalar_pld,
)

MAX_NONZERO = 4  # sum(q^2) <= 4 with entries in {-1, 0, 1}
MAX_SHIFT2 = MAX_NONZERO
MAX_TOTAL_DISPLACEMENT = 2 * MAX_NONZERO  # 2a + b <= 8


@dataclass(frozen=True)
class PatternResult:
    shift2_coordinates: int
    shift1_coordinates: int
    rounds: int
    k: int
    compositions_shift2: int
    compositions_shift1: int
    target_delta: float
    epsilon_upper: float | None
    unavoidable_delta_floor: float
    finite_epsilon_available: bool


@dataclass(frozen=True)
class EnvelopeResult:
    dimension: int
    rounds: int
    k: int
    assumption: str
    compositions_shift2: int
    target_delta: float
    field_sampler_bias_delta: float
    unavoidable_delta_floor: float
    epsilon_upper: float | None
    finite_epsilon_available: bool


def feasible_patterns() -> list[tuple[int, int]]:
    """All (a, b) with a shift-2 and b shift-1 coordinates admissible under the fixed bound."""
    patterns: list[tuple[int, int]] = []
    for a in range(MAX_SHIFT2 + 1):
        for b in range(MAX_TOTAL_DISPLACEMENT - 2 * a + 1):
            if a + b > 0:
                patterns.append((a, b))
    return patterns


def compose_profiles(first: ComposedPrivacyProfile, second: ComposedPrivacyProfile) -> ComposedPrivacyProfile:
    """Convolve two composed privacy-loss profiles that share the same grid step."""
    if first.grid_step != second.grid_step:
        raise ValueError("profiles must share a grid step")
    composed = fftconvolve(first.loss_probabilities, second.loss_probabilities)
    composed[composed < 0.0] = 0.0
    expected_finite_mass = first.finite_mass * second.finite_mass
    observed_mass = float(composed.sum())
    mass_error = abs(observed_mass - expected_finite_mass)
    if observed_mass > 0:
        composed *= expected_finite_mass / observed_mass
    result = ComposedPrivacyProfile.__new__(ComposedPrivacyProfile)
    result.k = first.k
    result.shift = max(first.shift, second.shift)
    result.compositions = first.compositions + second.compositions
    result.grid_step = first.grid_step
    result.loss_probabilities = composed
    result.offset = first.offset + second.offset
    result.finite_mass = expected_finite_mass
    result.infinity_mass = 1.0 - expected_finite_mass
    result.numerical_guard = first.numerical_guard + second.numerical_guard + mass_error
    return result


def pattern_profile(*, k: int, shift2: int, shift1: int, grid_step: float, numerical_guard: float) -> ComposedPrivacyProfile:
    profiles = []
    if shift2:
        profiles.append(ComposedPrivacyProfile(k=k, shift=2, compositions=shift2, grid_step=grid_step, numerical_guard=numerical_guard))
    if shift1:
        profiles.append(ComposedPrivacyProfile(k=k, shift=1, compositions=shift1, grid_step=grid_step, numerical_guard=numerical_guard))
    if not profiles:
        raise ValueError("pattern must contain at least one displaced coordinate")
    profile = profiles[0]
    for other in profiles[1:]:
        profile = compose_profiles(profile, other)
    return profile


def account_pattern(*, a: int, b: int, rounds: int, k: int, target_delta: float, grid_step: float, numerical_guard: float) -> PatternResult:
    profile = pattern_profile(k=k, shift2=a * rounds, shift1=b * rounds, grid_step=grid_step, numerical_guard=numerical_guard)
    epsilon = profile.epsilon_for_delta(target_delta)
    return PatternResult(
        shift2_coordinates=a,
        shift1_coordinates=b,
        rounds=rounds,
        k=k,
        compositions_shift2=a * rounds,
        compositions_shift1=b * rounds,
        target_delta=target_delta,
        epsilon_upper=epsilon,
        unavoidable_delta_floor=profile.infinity_mass,
        finite_epsilon_available=epsilon is not None,
    )


def account_full_envelope(*, dimension: int, rounds: int, k: int, target_delta: float) -> EnvelopeResult:
    """Every coordinate may move by 2 (C_q^2 = d): the envelope behind the earlier extrapolation."""
    compositions = dimension * rounds
    _, scalar_infinity = scalar_pld(k, 2)
    floor = -math.expm1(compositions * math.log1p(-scalar_infinity))
    field_bias = field_low_bit_bias_bound(bits_per_output=2 * k, outputs=compositions)
    epsilon = None
    if floor < target_delta - field_bias:
        profile = ComposedPrivacyProfile(k=k, shift=2, compositions=compositions)
        epsilon = profile.epsilon_for_delta(target_delta - field_bias)
    return EnvelopeResult(
        dimension=dimension,
        rounds=rounds,
        k=k,
        assumption="every coordinate may be displaced by 2 (clip bound grows with d)",
        compositions_shift2=compositions,
        target_delta=target_delta,
        field_sampler_bias_delta=field_bias,
        unavoidable_delta_floor=floor,
        epsilon_upper=epsilon,
        finite_epsilon_available=epsilon is not None,
    )


def run(*, rounds_list: list[int], k: int, target_delta: float, grid_step: float, numerical_guard: float) -> dict[str, object]:
    pattern_tables: dict[str, object] = {}
    for rounds in rounds_list:
        results = [
            account_pattern(a=a, b=b, rounds=rounds, k=k, target_delta=target_delta, grid_step=grid_step, numerical_guard=numerical_guard)
            for a, b in feasible_patterns()
        ]
        finite = [r for r in results if r.epsilon_upper is not None]
        worst = max(finite, key=lambda r: r.epsilon_upper) if finite else None
        pattern_tables[str(rounds)] = {
            "rounds": rounds,
            "patterns": [asdict(r) for r in results],
            "worst_case": asdict(worst) if worst else None,
            "all_patterns_finite": all(r.finite_epsilon_available for r in results),
        }
    envelopes = [
        asdict(account_full_envelope(dimension=d, rounds=r, k=k, target_delta=target_delta))
        for d, r in [(4, 10), (385, 10), (1991, 10), (385, 20), (1991, 20)]
    ]
    return {
        "k": k,
        "target_delta": target_delta,
        "grid_step": grid_step,
        "numerical_guard": numerical_guard,
        "fixed_bound": {"entries": "{-1,0,1}", "max_sum_sq": MAX_NONZERO, "max_nonzero_per_update": MAX_NONZERO},
        "feasibility": "a <= 4 shift-2 coordinates, b shift-1 coordinates, 2a + b <= 8; independent of d >= 4",
        "fixed_bound_patterns": pattern_tables,
        "full_envelope": envelopes,
        "scope": (
            "ideal independent centered-binomial noise, fixed non-adaptive displacement pattern per round, "
            "replacement client-level adjacency; not a statement about the full ZK transcript"
        ),
    }


def write_markdown(report: dict[str, object], path: Path) -> None:
    lines = [
        "# Fixed-L2-bound pattern accounting (k=%d, delta=%g)" % (report["k"], report["target_delta"]),
        "",
        "If `sum(q_clip^2) <= 4` with entries in {-1,0,1} is kept in any dimension d >= 4, two",
        "replacement-adjacent updates differ in at most `a <= 4` coordinates by 2 and `b` coordinates",
        "by 1 with `2a + b <= 8`. The tables list the composed epsilon upper bound for every feasible",
        "pattern; the worst case is a dimension-free bound for the fixed-bound mechanism.",
        "",
    ]
    for rounds, table in report["fixed_bound_patterns"].items():
        lines += [f"## Fixed bound, {rounds} rounds", "", "| a (shift 2) | b (shift 1) | compositions | epsilon upper | delta floor |", "|---:|---:|---:|---:|---:|"]
        for row in table["patterns"]:
            eps = "none" if row["epsilon_upper"] is None else f"{row['epsilon_upper']:.6f}"
            lines.append(
                f"| {row['shift2_coordinates']} | {row['shift1_coordinates']} | "
                f"{row['compositions_shift2']}x2 + {row['compositions_shift1']}x1 | {eps} | {row['unavoidable_delta_floor']:.3e} |"
            )
        worst = table["worst_case"]
        lines += ["", f"Worst case: a={worst['shift2_coordinates']}, b={worst['shift1_coordinates']}, epsilon <= {worst['epsilon_upper']:.6f}.", ""]
    lines += [
        "## Full-displacement envelope (every coordinate may move by 2, i.e. C_q^2 = d)",
        "",
        "| d | rounds | compositions | delta floor | field bias | epsilon upper |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["full_envelope"]:
        eps = "none (delta floor above target)" if row["epsilon_upper"] is None else f"{row['epsilon_upper']:.6f}"
        lines.append(
            f"| {row['dimension']} | {row['rounds']} | {row['compositions_shift2']} | {row['unavoidable_delta_floor']:.3e} | "
            f"{row['field_sampler_bias_delta']:.1e} | {eps} |"
        )
    lines += ["", f"Scope: {report['scope']}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--rounds", nargs="+", type=int, default=[10, 20])
    parser.add_argument("--k", type=int, default=16)
    parser.add_argument("--target-delta", type=float, default=1e-5)
    parser.add_argument("--grid-step", type=float, default=0.002)
    parser.add_argument("--numerical-guard", type=float, default=1e-10)
    args = parser.parse_args()
    report = run(
        rounds_list=args.rounds, k=args.k, target_delta=args.target_delta, grid_step=args.grid_step, numerical_guard=args.numerical_guard
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "fixed_norm_pattern_accounting.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, args.output_dir / "fixed_norm_pattern_accounting.md")
    for rounds, table in report["fixed_bound_patterns"].items():
        worst = table["worst_case"]
        print(f"rounds={rounds}: worst pattern a={worst['shift2_coordinates']} b={worst['shift1_coordinates']} epsilon<={worst['epsilon_upper']:.6f}")
    for row in report["full_envelope"]:
        print(f"envelope d={row['dimension']} rounds={row['rounds']}: floor={row['unavoidable_delta_floor']:.3e} epsilon={row['epsilon_upper']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
