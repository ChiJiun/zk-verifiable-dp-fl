"""Server-side judgement of one received proof.

The server copies the received ``proof.json`` bytes once, calls ``ezkl.verify`` on that copy with
its own fixed vk, settings and SRS (``ezkl_client_checks/server_setup``), decodes the instances of
the same copy with its own settings, and only then applies ``gate.decide``. Nothing the client
writes besides the proof itself (its ``summary.json`` flag, its settings, its vk) is read.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from proof_gated_round.gate import (
    Decision,
    PublicStatement,
    decide,
    decode_field_element,
    decode_public_statement,
    encode_field_element,
)

BASE_DIR = Path(__file__).resolve().parent
EZKL_ROLES = BASE_DIR / "ezkl_roles.py"
SERVER_DIR = BASE_DIR / "ezkl_client_checks" / "server_setup"
DEFAULT_PYTHON = ["conda", "run", "-n", "zkML", "python"]


def ezkl_python(explicit: Sequence[str] | None = None) -> list[str]:
    """Interpreter command with torch and ezkl: explicit argument, else PROOF_GATED_PYTHON, else conda zkML."""
    if explicit:
        return list(explicit)
    if os.environ.get("PROOF_GATED_PYTHON"):
        return os.environ["PROOF_GATED_PYTHON"].split()
    return list(DEFAULT_PYTHON)


def run_role(python_cmd: Sequence[str], *args: object) -> dict:
    res = subprocess.run(
        [*python_cmd, str(EZKL_ROLES), *(str(arg) for arg in args)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    json_lines = [line for line in res.stdout.splitlines() if line.strip().startswith("{")]
    if res.returncode != 0 or not json_lines:
        raise RuntimeError(f"ezkl_roles {args[0]} failed (exit {res.returncode}): {res.stderr.strip()[-800:]}")
    return json.loads(json_lines[-1])


@dataclass(frozen=True)
class Judgement:
    verified: bool
    verify_error: str
    statement: PublicStatement
    statement_error: str
    decision: Decision


def judge(
    proof_path: Path,
    submitted_q_noisy: Sequence[int],
    python_cmd: Sequence[str],
    *,
    server_dir: Path = SERVER_DIR,
) -> Judgement:
    with tempfile.TemporaryDirectory() as tmp:
        received = Path(tmp) / "proof.json"
        received.write_bytes(Path(proof_path).read_bytes())
        verification = run_role(python_cmd, "verify", server_dir, received)
        statement_error = ""
        try:
            settings = json.loads((server_dir / "settings.json").read_text(encoding="utf-8"))
            statement = decode_public_statement(json.loads(received.read_text(encoding="utf-8")), settings)
        except (ValueError, KeyError) as exc:
            statement = PublicStatement(float("inf"), float("inf"), tuple())
            statement_error = str(exc)
    verified = bool(verification["verified"])
    return Judgement(
        verified=verified,
        verify_error=str(verification.get("error", "")),
        statement=statement,
        statement_error=statement_error,
        decision=decide(verified=verified, statement=statement, submitted_q_noisy=submitted_q_noisy),
    )


def with_shifted_public_coordinate(proof: dict, settings: dict, coordinate: int, delta: int = 1) -> dict:
    """Copy of ``proof`` whose public q_noisy[coordinate] is moved by ``delta`` quantization units."""
    check_size = 1
    for dim in settings["model_instance_shapes"][0]:
        check_size *= int(dim)
    scale = int(settings["model_output_scales"][1])
    shifted = copy.deepcopy(proof)
    if len(shifted["instances"]) != 1:
        raise ValueError("expected a single instance column")
    column = shifted["instances"][0]
    index = check_size + coordinate
    value = int(round(decode_field_element(column[index], scale=scale)))
    column[index] = encode_field_element(value + delta, scale=scale)
    return shifted
