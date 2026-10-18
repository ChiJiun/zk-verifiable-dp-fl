"""
proof-gated aggregation - Actual proof-gated round using EZKL-backed client checks.

Review fix (2026-10-18): the check model exposes the noisy update as a *public* output, and
the server (``gate.py``) decides acceptance from the proof's public instances only. The
vector a client asks to aggregate must equal the proven public ``q_noisy``; artifact check
flags are never consulted. Keeping a valid proof while submitting a different vector is
exercised explicitly and must be rejected.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
DEMO_DIR = BASE_DIR / "ezkl_client_checks"
ARTIFACTS_DIR = ROOT_DIR / "constraint_artifacts" / "results" / "artifacts" / "scale_10000"
os.chdir(BASE_DIR)

from proof_gated_round.gate import (  # noqa: E402
    RECOMMENDED_POLICY,
    Decision,
    PublicStatement,
    aggregate_accepted,
    decide,
    decode_public_statement,
)

DEFAULT_PYTHON = ["conda", "run", "-n", "zkML", "python"]


CHECK_MODEL_CODE = """\
from __future__ import annotations
import torch
import torch.nn as nn

class ConstraintCheckModel(nn.Module):
    \"\"\"Outputs (checks, public_q_noisy). Both outputs are public in the EZKL circuit, so the
    proof's statement contains the noisy update that the server will aggregate.\"\"\"

    def forward(self, packed: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        q_clipped = packed[:, 0:10]
        q_noise = packed[:, 10:20]
        q_noisy = packed[:, 20:30]
        expected_noisy = q_clipped + q_noise
        clip_sum_sq = torch.sum(q_clipped * q_clipped, dim=1, keepdim=True)
        relation_sum_sq = torch.sum((q_noisy - expected_noisy) ** 2, dim=1, keepdim=True)
        checks = torch.cat([clip_sum_sq, relation_sum_sq], dim=1)
        return checks, q_noisy
"""


EXPORT_MODEL_CODE = """\
from __future__ import annotations
import json
from pathlib import Path
import torch
from constraint_model import ConstraintCheckModel

base = Path(__file__).resolve().parent
artifact = json.loads((base / "artifact.json").read_text(encoding="utf-8"))
packed = torch.tensor([artifact["witness"]["q_clipped"] + artifact["witness"]["q_noise"] + artifact["witness"]["q_noisy"]], dtype=torch.float32)

model = ConstraintCheckModel().eval()
torch.onnx.export(
    model,
    packed,
    base / "constraint_check.onnx",
    input_names=["packed"],
    output_names=["checks", "public_q_noisy"],
    opset_version=18,
)
"""


PIPELINE_CODE = """\
from __future__ import annotations
import json
import time
from pathlib import Path
import torch
import ezkl
from constraint_model import ConstraintCheckModel

base = Path(__file__).resolve().parent
artifact = json.loads((base / "artifact.json").read_text(encoding="utf-8"))

packed = torch.tensor([artifact["witness"]["q_clipped"] + artifact["witness"]["q_noise"] + artifact["witness"]["q_noisy"]], dtype=torch.float32)
model = ConstraintCheckModel().eval()
checks, public_q_noisy = model(packed)

(base / "input.json").write_text(json.dumps({"input_data": packed.tolist()}), encoding="utf-8")

onnx_path = base / "constraint_check.onnx"
settings = base / "settings.json"
compiled = base / "network.ezkl"
srs = base / "kzg.srs"
pk = base / "pk.key"
vk = base / "vk.key"
witness = base / "witness.json"
proof = base / "proof.json"

ezkl.gen_settings(str(onnx_path), str(settings))
ezkl.calibrate_settings(str(base / "input.json"), str(onnx_path), str(settings), "resources")
ezkl.compile_circuit(str(onnx_path), str(compiled), str(settings))
logrows = json.loads(settings.read_text(encoding="utf-8"))["run_args"]["logrows"]
ezkl.gen_srs(str(srs), logrows)
ezkl.setup(str(compiled), str(vk), str(pk), str(srs))
ezkl.gen_witness(str(base / "input.json"), str(compiled), str(witness))
started = time.perf_counter()
ezkl.prove(str(witness), str(compiled), str(pk), str(proof), "single", str(srs))
prove_seconds = time.perf_counter() - started
started = time.perf_counter()
verified = ezkl.verify(str(proof), str(settings), str(vk), str(srs), False)
verify_seconds = time.perf_counter() - started

# Informational only: the server never reads these; it decodes proof.json instances.
summary = {
    "verified": bool(verified),
    "prove_seconds": prove_seconds,
    "verify_seconds": verify_seconds,
    "float32_model_outputs": {
        "clip_sum_sq": checks[0][0].item(),
        "relation_sum_sq": checks[0][1].item(),
        "public_q_noisy": [int(v) for v in public_q_noisy[0].tolist()],
    },
}
(base / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
"""


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_case_dir(client_id: int, case_name: str) -> Path:
    case_dir = DEMO_DIR / f"client_{client_id}_{case_name}"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "constraint_model.py").write_text(CHECK_MODEL_CODE, encoding="utf-8")
    (case_dir / "export_model.py").write_text(EXPORT_MODEL_CODE, encoding="utf-8")
    (case_dir / "pipeline.py").write_text(PIPELINE_CODE, encoding="utf-8")
    return case_dir


def run_prover_python(python_cmd: list[str], script_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*python_cmd, str(script_path)],
        cwd=script_path.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def check_artifact_policy(artifact: dict) -> bool:
    public = artifact["public_inputs"]
    return (
        int(public["scale"]) == RECOMMENDED_POLICY.scale
        and int(public["clip_rhs_bound_sq"]) == RECOMMENDED_POLICY.clip_rhs_bound_sq
        and int(public["slack_abs"]) == RECOMMENDED_POLICY.slack_abs
    )


def run_case(client_id: int, case_name: str, python_cmd: list[str]) -> dict[str, object]:
    source_artifact = ARTIFACTS_DIR / f"client_{client_id}_{case_name}.json"
    case_dir = prepare_case_dir(client_id, case_name)
    (case_dir / "artifact.json").write_text(source_artifact.read_text(encoding="utf-8"), encoding="utf-8")

    export_res = run_prover_python(python_cmd, case_dir / "export_model.py")
    pipeline_res = run_prover_python(python_cmd, case_dir / "pipeline.py")

    summary_path = case_dir / "summary.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    artifact = load_json(source_artifact)
    submitted_q_noisy = [int(v) for v in artifact["witness"]["q_noisy"]]
    verified = bool(summary.get("verified", False))

    statement: PublicStatement | None = None
    statement_error = ""
    if (case_dir / "proof.json").is_file() and (case_dir / "settings.json").is_file():
        try:
            statement = decode_public_statement(load_json(case_dir / "proof.json"), load_json(case_dir / "settings.json"))
        except (ValueError, KeyError) as exc:
            statement_error = str(exc)
    if statement is None:
        statement = PublicStatement(float("inf"), float("inf"), tuple())
        verified = False

    decision = decide(verified=verified, statement=statement, submitted_q_noisy=submitted_q_noisy)

    # Same valid proof, but the client submits a vector that differs in one coordinate.
    shifted = list(submitted_q_noisy)
    if shifted:
        shifted[0] += 1
    shifted_decision = decide(verified=verified, statement=statement, submitted_q_noisy=shifted)

    return {
        "client_id": client_id,
        "case_name": case_name,
        "verified": verified,
        "clip_ok": decision.clip_ok,
        "relation_ok": decision.relation_ok,
        "binding_ok": decision.binding_ok,
        "accepted": decision.accepted,
        "reasons": "; ".join(decision.reasons),
        "shifted_vector_rejected": not shifted_decision.accepted,
        "policy_matches_artifact": check_artifact_policy(artifact),
        "statement": statement,
        "decision": decision,
        "submitted_q_noisy": submitted_q_noisy,
        "statement_error": statement_error,
        "summary_path": str(summary_path.relative_to(ROOT_DIR)),
        "prove_seconds": summary.get("prove_seconds"),
        "verify_seconds": summary.get("verify_seconds"),
        "export_returncode": export_res.returncode,
        "pipeline_returncode": pipeline_res.returncode,
        "stdout_tail": (pipeline_res.stdout or "").strip()[-300:],
        "stderr_tail": (pipeline_res.stderr or "").strip()[-300:],
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
        "clip_ok",
        "relation_ok",
        "binding_ok",
        "accepted",
        "shifted_vector_rejected",
        "policy_matches_artifact",
        "reasons",
        "summary_path",
        "export_returncode",
        "pipeline_returncode",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{k: row[k] for k in fieldnames} for row in rows])


def write_statements(rows: list[dict[str, object]], swaps: list[dict[str, object]], output_path: Path) -> None:
    payload = {
        "policy": {
            "scale": RECOMMENDED_POLICY.scale,
            "clip_rhs_bound_sq": RECOMMENDED_POLICY.clip_rhs_bound_sq,
            "slack_abs": RECOMMENDED_POLICY.slack_abs,
        },
        "clients": [
            {
                "client_id": row["client_id"],
                "case_name": row["case_name"],
                "verified": row["verified"],
                "public_statement": row["statement"].to_json(),
                "submitted_q_noisy": row["submitted_q_noisy"],
                "decision": row["decision"].to_json(),
                "shifted_vector_rejected": row["shifted_vector_rejected"],
                "statement_error": row["statement_error"],
                "prove_seconds": row["prove_seconds"],
                "verify_seconds": row["verify_seconds"],
            }
            for row in rows
        ],
        "cross_client_swaps": swaps,
        "note": (
            "Acceptance and the aggregated vector come from proof.json instances decoded by gate.py; "
            "artifact.json check flags are not used. Vectors under public_statement are the proven ones."
        ),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_summary(
    rows: list[dict[str, object]],
    swaps: list[dict[str, object]],
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
    lines.extend(
        [
            "",
            "Interpretation:",
            "- This experiment runs actual EZKL-backed client checks before aggregation.",
            "- The proof statement is (clip_sum_sq, relation_sum_sq, q_noisy); the server decodes it from proof.json",
            "  instances, re-derives clip/relation from the recommended profile and only aggregates the proven q_noisy.",
            "- A submitted vector that differs from the proven q_noisy is rejected even though the proof verifies,",
            "  so a valid proof cannot be reused to aggregate a different update.",
            "- Local training provenance is still outside the statement (see the threat model).",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


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
    if args.python:
        python_cmd = list(args.python)
    elif os.environ.get("PROOF_GATED_PYTHON"):
        python_cmd = os.environ["PROOF_GATED_PYTHON"].split()
    else:
        python_cmd = DEFAULT_PYTHON

    print("=" * 60)
    print("proof-gated aggregation - Proof-Gated Round")
    print("=" * 60)

    rows: list[dict[str, object]] = []
    for client_id in range(3):
        case_name = "tampered_noisy_profile" if client_id == args.tampered_client else "honest_profile"
        print(f"Running client {client_id} -> {case_name}")
        row = run_case(client_id, case_name, python_cmd)
        print(f"  verified={row['verified']} accepted={row['accepted']} reasons={row['reasons'] or '-'}")
        if row["pipeline_returncode"] != 0:
            print(f"  pipeline stderr tail: {row['stderr_tail']}")
        rows.append(row)

    swaps = cross_client_swaps(rows)
    accepted_average = aggregate_accepted([row["statement"] for row in rows], [row["decision"] for row in rows])

    write_rows(rows, RESULTS_DIR / "proof_gated_round.csv")
    write_statements(rows, swaps, RESULTS_DIR / "statements.json")
    write_aggregate(RESULTS_DIR / "accepted_aggregate.json", accepted_average)
    write_summary(rows, swaps, RESULTS_DIR / "summary.md", args.tampered_client, accepted_average)
    print(f"Results saved to: {RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
