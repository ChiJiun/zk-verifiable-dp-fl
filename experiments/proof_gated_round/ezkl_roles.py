"""EZKL side of the proof-gated round. Run with an interpreter that has torch and ezkl installed.

Subcommands, one per party:

- ``server-setup DIR``: the server alone exports the check circuit, fixes settings.json without
  calibrating on any client data, generates the SRS and the key pair. Clients receive the compiled
  circuit, pk and SRS; the server keeps vk, settings and SRS for verification.
- ``client-prove SERVER_DIR ARTIFACT OUT_DIR``: a client proves its packed update with the
  server's compiled circuit, pk and SRS.
- ``verify SETUP_DIR PROOF``: ``ezkl.verify`` against the vk, settings and SRS in SETUP_DIR.
- ``foreign-circuit ARTIFACT OUT_DIR``: a malicious client builds its own circuit whose checks are
  always zero, runs its own setup and proves. Used to show the server's fixed vk rejects it.

Each subcommand prints one JSON line on stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import ezkl
import torch
import torch.nn as nn

PACKED_DIM = 30


class ConstraintCheckModel(nn.Module):
    """Outputs (checks, public_q_noisy). Both outputs are public, so the proof's statement contains
    the noisy update the server aggregates."""

    def forward(self, packed: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        q_clipped = packed[:, 0:10]
        q_noise = packed[:, 10:20]
        q_noisy = packed[:, 20:30]
        expected_noisy = q_clipped + q_noise
        clip_sum_sq = torch.sum(q_clipped * q_clipped, dim=1, keepdim=True)
        relation_sum_sq = torch.sum((q_noisy - expected_noisy) ** 2, dim=1, keepdim=True)
        checks = torch.cat([clip_sum_sq, relation_sum_sq], dim=1)
        return checks, q_noisy


class ForeignCheckModel(nn.Module):
    """Malicious circuit with the same public output shapes whose checks never fail."""

    def forward(self, packed: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        q_noisy = packed[:, 20:30]
        checks = packed[:, 0:2] * 0
        return checks, q_noisy


def fixed_run_args() -> ezkl.PyRunArgs:
    run_args = ezkl.PyRunArgs()
    run_args.input_scale = 13
    run_args.param_scale = 13
    run_args.scale_rebase_multiplier = 10
    run_args.logrows = 7
    run_args.num_inner_cols = 2
    run_args.lookup_range = (0, 0)
    run_args.input_visibility = "private"
    run_args.output_visibility = "public"
    run_args.param_visibility = "private"
    return run_args


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packed_input(artifact: dict) -> list[list[int]]:
    witness = artifact["witness"]
    return [witness["q_clipped"] + witness["q_noise"] + witness["q_noisy"]]


def build_setup(model: nn.Module, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = out_dir / "constraint_check.onnx"
    settings = out_dir / "settings.json"
    compiled = out_dir / "network.ezkl"
    srs = out_dir / "kzg.srs"
    vk = out_dir / "vk.key"
    pk = out_dir / "pk.key"
    torch.onnx.export(
        model.eval(),
        torch.zeros(1, PACKED_DIM),
        onnx_path,
        input_names=["packed"],
        output_names=["checks", "public_q_noisy"],
        opset_version=18,
    )
    if not ezkl.gen_settings(str(onnx_path), str(settings), py_run_args=fixed_run_args()):
        raise RuntimeError("gen_settings failed")
    if not ezkl.compile_circuit(str(onnx_path), str(compiled), str(settings)):
        raise RuntimeError("compile_circuit failed")
    logrows = json.loads(settings.read_text(encoding="utf-8"))["run_args"]["logrows"]
    # Locally generated test SRS; a deployment would load a ceremony SRS instead.
    ezkl.gen_srs(str(srs), logrows)
    if not ezkl.setup(str(compiled), str(vk), str(pk), str(srs)):
        raise RuntimeError("setup failed")
    return {name: sha256(out_dir / name) for name in ("settings.json", "network.ezkl", "kzg.srs", "vk.key")}


def prove(compiled: Path, pk: Path, srs: Path, artifact: dict, out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    input_path = out_dir / "input.json"
    witness = out_dir / "witness.json"
    proof = out_dir / "proof.json"
    input_path.write_text(json.dumps({"input_data": packed_input(artifact)}), encoding="utf-8")
    ezkl.gen_witness(str(input_path), str(compiled), str(witness))
    started = time.perf_counter()
    ezkl.prove(str(witness), str(compiled), str(pk), str(proof), "single", str(srs))
    return {"prove_seconds": time.perf_counter() - started}


def verify(setup_dir: Path, proof: Path) -> dict[str, object]:
    started = time.perf_counter()
    try:
        verified = bool(
            ezkl.verify(
                str(proof),
                str(setup_dir / "settings.json"),
                str(setup_dir / "vk.key"),
                str(setup_dir / "kzg.srs"),
                False,
            )
        )
        error = ""
    except Exception as exc:  # EZKL raises on proofs it cannot parse or that fail the constraint system
        verified = False
        error = str(exc)
    return {"verified": verified, "error": error, "verify_seconds": time.perf_counter() - started}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("server-setup")
    p.add_argument("out_dir", type=Path)
    p = sub.add_parser("client-prove")
    p.add_argument("server_dir", type=Path)
    p.add_argument("artifact", type=Path)
    p.add_argument("out_dir", type=Path)
    p = sub.add_parser("verify")
    p.add_argument("setup_dir", type=Path)
    p.add_argument("proof", type=Path)
    p = sub.add_parser("foreign-circuit")
    p.add_argument("artifact", type=Path)
    p.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    if args.command == "server-setup":
        result: dict[str, object] = {"sha256": build_setup(ConstraintCheckModel(), args.out_dir)}
    elif args.command == "client-prove":
        artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
        server = args.server_dir
        result = prove(server / "network.ezkl", server / "pk.key", server / "kzg.srs", artifact, args.out_dir)
        # Informational only: the server never reads this flag.
        result["client_reported_verified"] = verify(server, args.out_dir / "proof.json")["verified"]
        (args.out_dir / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    elif args.command == "verify":
        result = verify(args.setup_dir, args.proof)
    else:
        artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
        out = args.out_dir
        result = {"sha256": build_setup(ForeignCheckModel(), out)}
        result.update(prove(out / "network.ezkl", out / "pk.key", out / "kzg.srs", artifact, out))
        result["client_reported_verified"] = verify(out, out / "proof.json")["verified"]
        (out / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
