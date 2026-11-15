"""Server-side acceptance for the EZKL constraint line.

The statement that ``ezkl.verify`` actually checks is the list of public field
elements in ``proof.json`` (``instances``), not the client's ``artifact.json`` and
not the prover-written ``pretty_public_inputs`` block. The check model therefore
exposes the noisy update itself as a public output next to the two check sums, and
the server:

1. decodes ``instances`` into ``(clip_sum_sq, relation_sum_sq, q_noisy)``;
2. re-derives the clip and relation decisions from the fixed recommended profile,
   ignoring any ``checks`` flags shipped by the client;
3. binds the update the client asks to aggregate to the proven ``q_noisy``.

A proof that verifies for one vector can therefore not be reused to push a
different vector into the aggregate (see ``test_gate.py``).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

# Scalar field of BN254 / bn256, the curve EZKL uses for its KZG commitments
# (``run_args.commitment == "KZG"``). Negative fixed-point values are encoded as p - x.
BN254_SCALAR_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617

# The public q_noisy coordinates must decode to exact integers.
INTEGER_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Policy:
    """Fixed server policy for the recommended constraint profile."""

    scale: int = 10000
    clip_rhs_bound_sq: int = 100_000_000  # (C * scale)^2 with C = 1.0
    slack_abs: int = 420_100  # 4201 ppm of the bound


RECOMMENDED_POLICY = Policy()


@dataclass(frozen=True)
class PublicStatement:
    clip_sum_sq: float
    relation_sum_sq: float
    q_noisy: tuple[int, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "clip_sum_sq": self.clip_sum_sq,
            "relation_sum_sq": self.relation_sum_sq,
            "q_noisy": list(self.q_noisy),
        }


@dataclass(frozen=True)
class Decision:
    verified: bool
    clip_ok: bool
    relation_ok: bool
    binding_ok: bool
    accepted: bool
    reasons: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


def decode_field_element(hex_le: str, *, scale: int, modulus: int = BN254_SCALAR_MODULUS) -> float:
    """Decode one little-endian hex field element written by EZKL into a signed fixed-point value."""
    value = int.from_bytes(bytes.fromhex(hex_le), "little")
    if value >= modulus:
        raise ValueError("field element is not reduced modulo the scalar field")
    if value > modulus // 2:
        value -= modulus
    return value / float(1 << scale)


def encode_field_element(value: int, *, scale: int, modulus: int = BN254_SCALAR_MODULUS) -> str:
    """Inverse of :func:`decode_field_element` for integer-valued fixed-point outputs (used by tests)."""
    scaled = int(value) << scale
    if scaled < 0:
        scaled += modulus
    return scaled.to_bytes(32, "little").hex()


def decode_instances(proof: dict, settings: dict) -> list[list[float]]:
    """Split the proof's public instances into the model outputs declared in settings.json."""
    shapes = settings["model_instance_shapes"]
    scales = settings["model_output_scales"]
    if len(shapes) != len(scales):
        raise ValueError("settings.json declares a different number of output shapes and scales")
    flat = [element for column in proof["instances"] for element in column]
    outputs: list[list[float]] = []
    cursor = 0
    for shape, scale in zip(shapes, scales):
        size = math.prod(int(dim) for dim in shape)
        chunk = flat[cursor : cursor + size]
        if len(chunk) != size:
            raise ValueError("proof instances are shorter than the declared output shapes")
        outputs.append([decode_field_element(element, scale=int(scale)) for element in chunk])
        cursor += size
    if cursor != len(flat):
        raise ValueError("proof instances contain elements beyond the declared outputs")
    return outputs


def public_statement_from_outputs(outputs: Sequence[Sequence[float]]) -> PublicStatement:
    """Interpret the two public outputs of ``ConstraintCheckModel`` (checks, public_q_noisy)."""
    if len(outputs) != 2:
        raise ValueError(
            "expected two public outputs (checks, public_q_noisy); a proof whose statement does not "
            "include q_noisy cannot bind the aggregated vector"
        )
    checks, q_noisy_raw = outputs
    if len(checks) != 2:
        raise ValueError("checks output must contain clip_sum_sq and relation_sum_sq")
    q_noisy: list[int] = []
    for value in q_noisy_raw:
        nearest = round(value)
        if abs(value - nearest) > INTEGER_TOLERANCE:
            raise ValueError(f"public q_noisy coordinate {value!r} is not an integer")
        q_noisy.append(int(nearest))
    return PublicStatement(clip_sum_sq=float(checks[0]), relation_sum_sq=float(checks[1]), q_noisy=tuple(q_noisy))


def decode_public_statement(proof: dict, settings: dict) -> PublicStatement:
    return public_statement_from_outputs(decode_instances(proof, settings))


def decide(
    *,
    verified: bool,
    statement: PublicStatement,
    submitted_q_noisy: Sequence[int],
    policy: Policy = RECOMMENDED_POLICY,
) -> Decision:
    """Accept only if the proof verifies, the proven sums satisfy the policy, and the submitted
    vector is exactly the proven one. Client-supplied check flags are never consulted."""
    reasons: list[str] = []
    if not verified:
        reasons.append("proof did not verify")
    clip_ok = statement.clip_sum_sq <= policy.clip_rhs_bound_sq + policy.slack_abs
    if not clip_ok:
        reasons.append("proven clip_sum_sq exceeds bound + slack")
    # Private inputs are not forced to be integers (EZKL quantizes them at input scale 13), so a
    # residual can be fractional, e.g. 0.25 from a 0.5 offset in q_noise. Only an exact zero passes.
    relation_ok = statement.relation_sum_sq == 0.0
    if not relation_ok:
        reasons.append("proven relation residual is non-zero")
    binding_ok = tuple(int(value) for value in submitted_q_noisy) == statement.q_noisy
    if not binding_ok:
        reasons.append("submitted q_noisy differs from the proven public q_noisy")
    accepted = verified and clip_ok and relation_ok and binding_ok
    return Decision(
        verified=bool(verified),
        clip_ok=clip_ok,
        relation_ok=relation_ok,
        binding_ok=binding_ok,
        accepted=accepted,
        reasons=tuple(reasons),
    )


def aggregate_accepted(statements: Sequence[PublicStatement], decisions: Sequence[Decision]) -> list[float]:
    """Average the *proven* vectors of accepted clients; submitted vectors are never aggregated."""
    vectors = [list(statement.q_noisy) for statement, decision in zip(statements, decisions) if decision.accepted]
    if not vectors:
        return []
    return [sum(values) / len(vectors) for values in zip(*vectors)]
