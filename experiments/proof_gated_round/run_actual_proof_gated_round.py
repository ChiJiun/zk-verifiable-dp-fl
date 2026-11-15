"""
proof-gated aggregation - Actual proof-gated round using EZKL-backed client checks.

Review fix (2026-10-18): the check model exposes the noisy update as a *public* output, and
the server (``gate.py``) decides acceptance from the proof's public instances only. The
vector a client asks to aggregate must equal the proven public ``q_noisy``; artifact check
flags are never consulted. Keeping a valid proof while submitting a different vector is
exercised explicitly and must be rejected.

Review fix (2026-10-20): the server alone fixes the circuit, settings, SRS and keys
(``ezkl_roles.py server-setup``); clients prove with the server's compiled circuit, pk and SRS.
The server verifies each received proof itself with its fixed vk, settings and SRS, then decodes
the instances of that same proof (``server_verifier.judge``). Two rejection cases are run with
real EZKL: a proof made under a client's own circuit and vk, and a proof that fails verification
while the client's flag claims it verified.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
DEMO_DIR = BASE_DIR / "ezkl_client_checks"
ARTIFACTS_DIR = ROOT_DIR / "constraint_artifacts" / "results" / "artifacts" / "scale_10000"
FOREIGN_CIRCUIT_DIR = DEMO_DIR / "attack_foreign_circuit"
FAILED_PROOF_DIR = DEMO_DIR / "attack_failed_proof_true_flag"
os.chdir(BASE_DIR)

from proof_gated_round.gate import (  # noqa: E402
    RECOMMENDED_POLICY,
    aggregate_accepted,
    decide,
    decode_public_statement,
)
from proof_gated_round.server_verifier import (  # noqa: E402
    SERVER_DIR,
    ezkl_python,
    judge,
    run_role,
    with_shifted_public_coordinate,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_artifact_policy(artifact: dict) -> bool:
    public = artifact["public_inputs"]
    return (
        int(public["scale"]) == RECOMMENDED_POLICY.scale
        and int(public["clip_rhs_bound_sq"]) == RECOMMENDED_POLICY.clip_rhs_bound_sq
        and int(public["slack_abs"]) == RECOMMENDED_POLICY.slack_abs
    )


def run_case(client_id: int, case_name: str, python_cmd: list[str]) -> dict[str, object]:
    source_artifact = ARTIFACTS_DIR / f"client_{client_id}_{case_name}.json"
    case_dir = DEMO_DIR / f"client_{client_id}_{case_name}"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "artifact.json").write_text(source_artifact.read_text(encoding="utf-8"), encoding="utf-8")

    client = run_role(python_cmd, "client-prove", SERVER_DIR, case_dir / "artifact.json", case_dir)
    artifact = load_json(source_artifact)
    submitted_q_noisy = [int(v) for v in artifact["witness"]["q_noisy"]]
    judgement = judge(case_dir / "proof.json", submitted_q_noisy, python_cmd)

    # Same verified proof, but the client submits a vector that differs in one coordinate.
    shifted = list(submitted_q_noisy)
    if shifted:
        shifted[0] += 1
    shifted_decision = decide(verified=judgement.verified, statement=judgement.statement, submitted_q_noisy=shifted)

    decision = judgement.decision
    return {
        "client_id": client_id,
        "case_name": case_name,
        "verified": judgement.verified,
        "client_reported_verified": client["client_reported_verified"],
        "clip_ok": decision.clip_ok,
        "relation_ok": decision.relation_ok,
        "binding_ok": decision.binding_ok,
        "accepted": decision.accepted,
        "reasons": "; ".join(decision.reasons),
        "shifted_vector_rejected": not shifted_decision.accepted,
        "policy_matches_artifact": check_artifact_policy(artifact),
        "statement": judgement.statement,
        "decision": decision,
        "submitted_q_noisy": submitted_q_noisy,
        "statement_error": judgement.statement_error,
        "verify_error": judgement.verify_error,
        "proof_path": (case_dir / "proof.json").relative_to(ROOT_DIR).as_posix(),
        "prove_seconds": client["prove_seconds"],
    }


def foreign_circuit_case(python_cmd: list[str], tampered_client: int) -> dict[str, object]:
    """A client that ignores the server's setup: its own circuit (checks always zero), own SRS and vk,
    proving the tampered client's vector. The proof verifies under its own vk only."""
    artifact_path = ARTIFACTS_DIR / f"client_{tampered_client}_tampered_noisy_profile.json"
    client = run_role(python_cmd, "foreign-circuit", artifact_path, FOREIGN_CIRCUIT_DIR)
    submitted = [int(v) for v in load_json(artifact_path)["witness"]["q_noisy"]]
    proof_path = FOREIGN_CIRCUIT_DIR / "proof.json"

    own_verified = bool(run_role(python_cmd, "verify", FOREIGN_CIRCUIT_DIR, proof_path)["verified"])
    own_statement = decode_public_statement(load_json(proof_path), load_json(FOREIGN_CIRCUIT_DIR / "settings.json"))
    if_client_setup_trusted = decide(verified=own_verified, statement=own_statement, submitted_q_noisy=submitted)

    judgement = judge(proof_path, submitted, python_cmd)
    return {
        "case": "foreign_circuit_and_vk",
        "proof_path": proof_path.relative_to(ROOT_DIR).as_posix(),
        "client_reported_verified": client["client_reported_verified"],
        "verified_under_client_vk": own_verified,
        "accepted_if_client_setup_trusted": if_client_setup_trusted.accepted,
        "server_verified": judgement.verified,
        "server_verify_error": judgement.verify_error,
        "decision": judgement.decision.to_json(),
    }


def failed_proof_true_flag_case(python_cmd: list[str], honest_row: dict[str, object]) -> dict[str, object]:
    """Take an honest proof, move one public q_noisy coordinate by 1, submit that vector, and claim
    verified=True in the client's summary. Every decoded check passes, so only ezkl.verify can reject."""
    honest_proof = load_json(ROOT_DIR / str(honest_row["proof_path"]))
    forged = with_shifted_public_coordinate(honest_proof, load_json(SERVER_DIR / "settings.json"), coordinate=0)
    FAILED_PROOF_DIR.mkdir(parents=True, exist_ok=True)
    proof_path = FAILED_PROOF_DIR / "proof.json"
    proof_path.write_text(json.dumps(forged), encoding="utf-8")
    (FAILED_PROOF_DIR / "summary.json").write_text(
        json.dumps({"client_reported_verified": True, "derived_from": honest_row["proof_path"]}, indent=2),
        encoding="utf-8",
    )
    submitted = list(honest_row["submitted_q_noisy"])
    submitted[0] += 1

    judgement = judge(proof_path, submitted, python_cmd)
    return {
        "case": "failed_proof_with_true_flag",
        "proof_path": proof_path.relative_to(ROOT_DIR).as_posix(),
        "client_reported_verified": True,
        "server_verified": judgement.verified,
        "server_verify_error": judgement.verify_error,
        "decision": judgement.decision.to_json(),
    }


def cross_client_swaps(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Keep client i's valid proof, submit client j's vector: every pair must be rejected."""
    swaps: list[dict[str, object]] = []
    for row in rows:
        if not row["accepted"]:
            continue
        for other in rows:
            if other is row:
                continue
            swapped = decide(
                verified=bool(row["verified"]),
                statement=row["statement"],
                submitted_q_noisy=other["submitted_q_noisy"],
            )
            swaps.append(
                {
                    "proof_client": row["client_id"],
                    "vector_client": other["client_id"],
                    "accepted": swapped.accepted,
                    "reasons": list(swapped.reasons),
                }
            )
    return swaps


def write_rows(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "client_id",
        "case_name",
        "verified",
        "client_reported_verified",
        "clip_ok",
        "relation_ok",
        "binding_ok",
        "accepted",
        "shifted_vector_rejected",
        "policy_matches_artifact",
        "reasons",
        "proof_path",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{k: row[k] for k in fieldnames} for row in rows])


def write_statements(
    rows: list[dict[str, object]],
    swaps: list[dict[str, object]],
    adversarial: list[dict[str, object]],
    server_setup: dict[str, object],
    output_path: Path,
) -> None:
    payload = {
        "policy": {
            "scale": RECOMMENDED_POLICY.scale,
            "clip_rhs_bound_sq": RECOMMENDED_POLICY.clip_rhs_bound_sq,
            "slack_abs": RECOMMENDED_POLICY.slack_abs,
        },
        "server_setup": {
            "dir": SERVER_DIR.relative_to(ROOT_DIR).as_posix(),
            "sha256": server_setup["sha256"],
            "srs": "ezkl.gen_srs test SRS generated by the server (single-machine simulation, not a ceremony SRS)",
        },
        "clients": [
            {
                "client_id": row["client_id"],
                "case_name": row["case_name"],
                "verified": row["verified"],
                "client_reported_verified": row["client_reported_verified"],
                "public_statement": row["statement"].to_json(),
                "submitted_q_noisy": row["submitted_q_noisy"],
                "decision": row["decision"].to_json(),
                "shifted_vector_rejected": row["shifted_vector_rejected"],
                "statement_error": row["statement_error"],
                "verify_error": row["verify_error"],
                "prove_seconds": row["prove_seconds"],
            }
            for row in rows
        ],
        "cross_client_swaps": swaps,
        "adversarial_cases": adversarial,
        "note": (
            "verified is the server's own ezkl.verify on the received proof with the server_setup vk, settings "
            "and SRS; the proven statement is decoded from the instances of that same proof with the server's "
            "settings. client_reported_verified is the client's self-check and is not used for any decision."
        ),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_summary(
    rows: list[dict[str, object]],
    swaps: list[dict[str, object]],
    adversarial: list[dict[str, object]],
    output_path: Path,
    tampered_client: int,
    accepted_average: list[float],
) -> None:
    accepted_rows = [row for row in rows if row["accepted"]]
    rejected_rows = [row for row in rows if not row["accepted"]]
    swaps_rejected = sum(1 for swap in swaps if not swap["accepted"])
    shifted_rejected = sum(1 for row in accepted_rows if row["shifted_vector_rejected"])
    lines = [
        "# proof-gated aggregation Proof-Gated Round Summary",
        "",
        "- Verification: the server runs ezkl.verify itself with its fixed vk, settings and test SRS",
        "  (ezkl_client_checks/server_setup), then decodes the instances of that same proof.",
        f"- Tampered client: {tampered_client}",
        f"- Accepted proofs: {len(accepted_rows)}/{len(rows)}",
        f"- Rejected proofs: {len(rejected_rows)}/{len(rows)}",
        f"- Tampered client accepted: {next(row['accepted'] for row in rows if row['client_id'] == tampered_client)}",
        f"- Accepted aggregate vector length: {len(accepted_average)}",
        f"- Valid proof + single-coordinate shifted submission rejected: {shifted_rejected}/{len(accepted_rows)}",
        f"- Valid proof + other client's vector rejected: {swaps_rejected}/{len(swaps)}",
        "",
        "Accepted clients:",
    ]
    lines.extend(
        f"- client {row['client_id']} ({row['case_name']}): verified={row['verified']}, clip_ok={row['clip_ok']}, "
        f"relation_ok={row['relation_ok']}, binding_ok={row['binding_ok']}"
        for row in accepted_rows
    )
    lines.extend(["", "Rejected clients:"])
    lines.extend(
        f"- client {row['client_id']} ({row['case_name']}): verified={row['verified']}, clip_ok={row['clip_ok']}, "
        f"relation_ok={row['relation_ok']}, binding_ok={row['binding_ok']} ({row['reasons']})"
        for row in rejected_rows
    )
    lines.extend(["", "Adversarial cases (real EZKL):"])
    for case in adversarial:
        decision = case["decision"]
        extra = ""
        if "verified_under_client_vk" in case:
            extra = (
                f", verified_under_client_vk={case['verified_under_client_vk']}, "
                f"accepted_if_client_setup_trusted={case['accepted_if_client_setup_trusted']}"
            )
        lines.append(
            f"- {case['case']}: client_reported_verified={case['client_reported_verified']}{extra}, "
            f"server_verified={case['server_verified']}, clip_ok={decision['clip_ok']}, "
            f"relation_ok={decision['relation_ok']}, binding_ok={decision['binding_ok']}, accepted={decision['accepted']}"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- This experiment runs actual EZKL-backed client checks before aggregation.",
            "- The server alone fixes the circuit, settings, SRS and keys; clients prove with the server's",
            "  compiled circuit, pk and SRS. The SRS is an ezkl.gen_srs test SRS, so this is a single-machine",
            "  simulation that trusts the server's setup, not a deployment with a ceremony SRS.",
            "- The proof statement is (clip_sum_sq, relation_sum_sq, q_noisy); the server decodes it from the",
            "  instances of the proof it verified, re-derives clip/relation from the recommended profile and only",
            "  aggregates the proven q_noisy.",
            "- A submitted vector that differs from the proven q_noisy is rejected even though the proof verifies,",
            "  so a valid proof cannot be reused to aggregate a different update.",
            "- A proof made under a client's own circuit and vk, or one that fails verification, is rejected",
            "  whatever the client reports about it.",
            "- Local training provenance is still outside the statement (see the threat model).",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_aggregate(output_path: Path, accepted_average: list[float]) -> None:
    output_path.write_text(json.dumps({"accepted_average_q_noisy": accepted_average}, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a proof-gated round with actual EZKL client checks")
    parser.add_argument("--tampered-client", type=int, default=1)
    parser.add_argument(
        "--python",
        nargs="+",
        default=None,
        help="Interpreter command that has torch and ezkl installed (default: the PROOF_GATED_PYTHON "
        "environment variable, else `conda run -n zkML python`).",
    )
    args = parser.parse_args()
    python_cmd = ezkl_python(args.python)

    print("=" * 60)
    print("proof-gated aggregation - Proof-Gated Round")
    print("=" * 60)

    print(f"Server setup -> {SERVER_DIR.relative_to(ROOT_DIR)}")
    server_setup = run_role(python_cmd, "server-setup", SERVER_DIR)

    rows: list[dict[str, object]] = []
    for client_id in range(3):
        case_name = "tampered_noisy_profile" if client_id == args.tampered_client else "honest_profile"
        print(f"Running client {client_id} -> {case_name}")
        row = run_case(client_id, case_name, python_cmd)
        print(f"  verified={row['verified']} accepted={row['accepted']} reasons={row['reasons'] or '-'}")
        rows.append(row)

    honest_row = next(row for row in rows if row["accepted"])
    adversarial = [
        foreign_circuit_case(python_cmd, args.tampered_client),
        failed_proof_true_flag_case(python_cmd, honest_row),
    ]
    for case in adversarial:
        print(f"Adversarial {case['case']}: server_verified={case['server_verified']} accepted={case['decision']['accepted']}")

    swaps = cross_client_swaps(rows)
    accepted_average = aggregate_accepted([row["statement"] for row in rows], [row["decision"] for row in rows])

    write_rows(rows, RESULTS_DIR / "proof_gated_round.csv")
    write_statements(rows, swaps, adversarial, server_setup, RESULTS_DIR / "statements.json")
    write_aggregate(RESULTS_DIR / "accepted_aggregate.json", accepted_average)
    write_summary(rows, swaps, adversarial, RESULTS_DIR / "summary.md", args.tampered_client, accepted_average)
    print(f"Results saved to: {RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
