"""Regression tests for the EZKL proof gate: the aggregated vector must be the proven one."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

EXPERIMENTS_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_ROOT))

from proof_gated_round.gate import (  # noqa: E402
    BN254_SCALAR_MODULUS,
    RECOMMENDED_POLICY,
    PublicStatement,
    aggregate_accepted,
    decide,
    decode_field_element,
    decode_instances,
    decode_public_statement,
    encode_field_element,
    public_statement_from_outputs,
)
from proof_gated_round.server_verifier import (  # noqa: E402
    SERVER_DIR,
    ezkl_python,
    judge,
    run_role,
    with_shifted_public_coordinate,
)

BASE_DIR = Path(__file__).resolve().parent
CASE_DIRS = {
    "honest_0": BASE_DIR / "ezkl_client_checks" / "client_0_honest_profile",
    "tampered_1": BASE_DIR / "ezkl_client_checks" / "client_1_tampered_noisy_profile",
    "honest_2": BASE_DIR / "ezkl_client_checks" / "client_2_honest_profile",
}
FOREIGN_CIRCUIT_DIR = BASE_DIR / "ezkl_client_checks" / "attack_foreign_circuit"
LEGACY_DEMO = EXPERIMENTS_ROOT / "ezkl_constraint_integration" / "ezkl_actual_demo" / "honest_profile"

HONEST_Q_NOISY = [279, 448, 2351, -2004, 3393, 42, 859, -1775, 550, -9720]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fake_proof(clip_sum_sq: int, relation_sum_sq: int, q_noisy: list[int], *, check_scale: int = 26, vector_scale: int = 13):
    """Build a proof/settings pair with the encoding EZKL writes, without running EZKL."""
    instances = [encode_field_element(clip_sum_sq, scale=check_scale), encode_field_element(relation_sum_sq, scale=check_scale)]
    instances += [encode_field_element(value, scale=vector_scale) for value in q_noisy]
    proof = {"instances": [instances]}
    settings = {"model_instance_shapes": [[1, 2], [1, len(q_noisy)]], "model_output_scales": [check_scale, vector_scale]}
    return proof, settings


class FieldDecodingTests(unittest.TestCase):
    def test_round_trip_signed_fixed_point(self) -> None:
        for value in (0, 1, -1, 9720, -9720, 99_337_085):
            for scale in (13, 26):
                encoded = encode_field_element(value, scale=scale)
                self.assertEqual(len(encoded), 64)
                self.assertEqual(decode_field_element(encoded, scale=scale), float(value))

    def test_negative_values_use_modular_complement(self) -> None:
        encoded = encode_field_element(-3, scale=0)
        self.assertEqual(int.from_bytes(bytes.fromhex(encoded), "little"), BN254_SCALAR_MODULUS - 3)
        self.assertEqual(decode_field_element(encoded, scale=0), -3.0)

    @unittest.skipUnless((LEGACY_DEMO / "proof.json").is_file(), "recorded EZKL demo proof not present")
    def test_decoder_matches_ezkl_pretty_outputs_on_recorded_proof(self) -> None:
        proof = load(LEGACY_DEMO / "proof.json")
        settings = load(LEGACY_DEMO / "settings.json")
        decoded = decode_instances(proof, settings)
        pretty = proof["pretty_public_inputs"]["rescaled_outputs"]
        self.assertEqual(len(decoded), len(pretty))
        for ours, theirs in zip(decoded, pretty):
            self.assertEqual([float(v) for v in ours], [float(v) for v in theirs])

    @unittest.skipUnless((LEGACY_DEMO / "proof.json").is_file(), "recorded EZKL demo proof not present")
    def test_legacy_statement_without_public_update_is_refused(self) -> None:
        proof = load(LEGACY_DEMO / "proof.json")
        settings = load(LEGACY_DEMO / "settings.json")
        with self.assertRaises(ValueError):
            decode_public_statement(proof, settings)


class DecisionTests(unittest.TestCase):
    def honest_statement(self) -> PublicStatement:
        proof, settings = fake_proof(98_890_825, 0, HONEST_Q_NOISY)
        return decode_public_statement(proof, settings)

    def test_honest_submission_is_accepted(self) -> None:
        statement = self.honest_statement()
        decision = decide(verified=True, statement=statement, submitted_q_noisy=HONEST_Q_NOISY)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.reasons, ())

    def test_valid_proof_with_swapped_vector_is_rejected(self) -> None:
        """The attack from the review: keep a proof that verifies, submit a different update."""
        statement = self.honest_statement()
        swapped = list(HONEST_Q_NOISY)
        swapped[3] += 1
        decision = decide(verified=True, statement=statement, submitted_q_noisy=swapped)
        self.assertTrue(decision.verified and decision.clip_ok and decision.relation_ok)
        self.assertFalse(decision.binding_ok)
        self.assertFalse(decision.accepted)
        self.assertIn("submitted q_noisy differs from the proven public q_noisy", decision.reasons)

        other_client_vector = [v * -1 for v in HONEST_Q_NOISY]
        self.assertFalse(decide(verified=True, statement=statement, submitted_q_noisy=other_client_vector).accepted)
        self.assertFalse(decide(verified=True, statement=statement, submitted_q_noisy=HONEST_Q_NOISY[:-1]).accepted)

    def test_relation_violation_is_rejected_from_public_residual_only(self) -> None:
        proof, settings = fake_proof(99_337_085, 1, HONEST_Q_NOISY)
        statement = decode_public_statement(proof, settings)
        # No artifact flags are consulted; a client claiming relation_ok=True changes nothing.
        decision = decide(verified=True, statement=statement, submitted_q_noisy=HONEST_Q_NOISY)
        self.assertFalse(decision.relation_ok)
        self.assertFalse(decision.accepted)

    def test_fractional_residual_is_rejected(self) -> None:
        """Private inputs may be fractional: a 0.5 offset in q_noise proves a residual of 0.25."""
        statement = PublicStatement(98_890_825.0, 0.25, tuple(HONEST_Q_NOISY))
        decision = decide(verified=True, statement=statement, submitted_q_noisy=HONEST_Q_NOISY)
        self.assertFalse(decision.relation_ok)
        self.assertFalse(decision.accepted)

    def test_known_boundary_unconstrained_noise_accepts_any_update(self) -> None:
        """Documents a limit, not a feature: q_noise is a private witness with no range check, so
        q_clipped = 0 and q_noise = q_noisy prove clip 0 and residual 0 for any vector. The EZKL gate
        cannot bound the update size; only in-circuit noise generation (the Halo2 line) can."""
        large = [1_000_000 if i % 2 == 0 else -1_000_000 for i in range(10)]
        proof, settings = fake_proof(0, 0, large)
        decision = decide(verified=True, statement=decode_public_statement(proof, settings), submitted_q_noisy=large)
        self.assertTrue(decision.accepted)

    def test_clip_violation_is_rejected(self) -> None:
        bound = RECOMMENDED_POLICY.clip_rhs_bound_sq + RECOMMENDED_POLICY.slack_abs
        proof, settings = fake_proof(bound + 1, 0, HONEST_Q_NOISY)
        decision = decide(verified=True, statement=decode_public_statement(proof, settings), submitted_q_noisy=HONEST_Q_NOISY)
        self.assertFalse(decision.clip_ok)
        self.assertFalse(decision.accepted)
        proof, settings = fake_proof(bound, 0, HONEST_Q_NOISY)
        self.assertTrue(
            decide(verified=True, statement=decode_public_statement(proof, settings), submitted_q_noisy=HONEST_Q_NOISY).clip_ok
        )

    def test_unverified_proof_is_rejected(self) -> None:
        decision = decide(verified=False, statement=self.honest_statement(), submitted_q_noisy=HONEST_Q_NOISY)
        self.assertFalse(decision.accepted)
        self.assertIn("proof did not verify", decision.reasons)

    def test_non_integer_public_vector_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            public_statement_from_outputs([[1.0, 0.0], [1.5, 2.0]])

    def test_aggregate_uses_proven_vectors_only(self) -> None:
        a = PublicStatement(1.0, 0.0, (1, 2, 3))
        b = PublicStatement(1.0, 0.0, (3, 2, 1))
        rejected = PublicStatement(1.0, 1.0, (100, 100, 100))
        decisions = [
            decide(verified=True, statement=a, submitted_q_noisy=[1, 2, 3]),
            decide(verified=True, statement=b, submitted_q_noisy=[3, 2, 1]),
            decide(verified=True, statement=rejected, submitted_q_noisy=[100, 100, 100]),
        ]
        self.assertEqual(aggregate_accepted([a, b, rejected], decisions), [2.0, 2.0, 2.0])


class RecordedProofTests(unittest.TestCase):
    """Run against the proofs regenerated by run_actual_proof_gated_round.py when they are present."""

    def setUp(self) -> None:
        if not (SERVER_DIR / "settings.json").is_file():
            self.skipTest("server settings.json not present")
        if not all((path / "proof.json").is_file() for path in CASE_DIRS.values()):
            self.skipTest("regenerated EZKL proofs not present")
        settings = load(SERVER_DIR / "settings.json")
        self.cases = {
            name: (load(path / "proof.json"), settings, load(path / "artifact.json")) for name, path in CASE_DIRS.items()
        }

    def test_public_statement_binds_the_artifact_vector(self) -> None:
        for name, (proof, settings, artifact) in self.cases.items():
            statement = decode_public_statement(proof, settings)
            self.assertEqual(list(statement.q_noisy), artifact["witness"]["q_noisy"], name)
            expected_clip = sum(v * v for v in artifact["witness"]["q_clipped"])
            self.assertLessEqual(abs(statement.clip_sum_sq - expected_clip), 64, name)

    def test_recorded_honest_proofs_accept_and_swaps_reject(self) -> None:
        honest_0 = decode_public_statement(*self.cases["honest_0"][:2])
        honest_2 = decode_public_statement(*self.cases["honest_2"][:2])
        tampered = decode_public_statement(*self.cases["tampered_1"][:2])
        self.assertTrue(decide(verified=True, statement=honest_0, submitted_q_noisy=honest_0.q_noisy).accepted)
        self.assertTrue(decide(verified=True, statement=honest_2, submitted_q_noisy=honest_2.q_noisy).accepted)
        self.assertFalse(decide(verified=True, statement=tampered, submitted_q_noisy=tampered.q_noisy).accepted)
        # Valid honest proof, tampered client's vector submitted in its place.
        self.assertFalse(decide(verified=True, statement=honest_0, submitted_q_noisy=tampered.q_noisy).accepted)
        self.assertFalse(decide(verified=True, statement=honest_0, submitted_q_noisy=honest_2.q_noisy).accepted)

    def test_recorded_boundary_and_fractional_cases(self) -> None:
        settings = load(SERVER_DIR / "settings.json")
        for name, accepted in (
            ("boundary_adaptive_noise", True),
            ("boundary_arbitrary_magnitude", True),
            ("attack_fractional_residual", False),
        ):
            case_dir = BASE_DIR / "ezkl_client_checks" / name
            if not (case_dir / "proof.json").is_file():
                self.skipTest(f"{name} not regenerated")
            statement = decode_public_statement(load(case_dir / "proof.json"), settings)
            submitted = [int(v) for v in load(case_dir / "artifact.json")["witness"]["q_noisy"]]
            self.assertEqual(decide(verified=True, statement=statement, submitted_q_noisy=submitted).accepted, accepted, name)
        tampered = load(CASE_DIRS["tampered_1"] / "artifact.json")["witness"]["q_noisy"]
        adaptive = decode_public_statement(load(BASE_DIR / "ezkl_client_checks" / "boundary_adaptive_noise" / "proof.json"), settings)
        # The rejected client's exact vector gets through once the change is moved into private q_noise.
        self.assertEqual(list(adaptive.q_noisy), [int(v) for v in tampered])


class ServerVerificationTests(unittest.TestCase):
    """The server runs ezkl.verify itself with its fixed vk, settings and SRS. Needs an interpreter with
    ezkl (PROOF_GATED_PYTHON or conda env zkML) and the server_setup keys regenerated by the runner."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.python_cmd = ezkl_python()
        if shutil.which(cls.python_cmd[0]) is None:
            raise unittest.SkipTest(f"{cls.python_cmd[0]} not found; EZKL interpreter unavailable")
        needed = [SERVER_DIR / name for name in ("settings.json", "vk.key", "kzg.srs")]
        needed += [path / "proof.json" for path in CASE_DIRS.values()]
        if not all(path.is_file() for path in needed):
            raise unittest.SkipTest("server_setup keys or regenerated proofs not present; run run_actual_proof_gated_round.py")

    def test_honest_proof_verifies_under_server_setup(self) -> None:
        artifact = load(CASE_DIRS["honest_0"] / "artifact.json")
        judgement = judge(CASE_DIRS["honest_0"] / "proof.json", artifact["witness"]["q_noisy"], self.python_cmd)
        self.assertTrue(judgement.verified, judgement.verify_error)
        self.assertTrue(judgement.decision.accepted)

    @unittest.skipUnless((FOREIGN_CIRCUIT_DIR / "vk.key").is_file(), "foreign-circuit attack not regenerated")
    def test_proof_under_client_chosen_circuit_and_vk_is_rejected(self) -> None:
        proof_path = FOREIGN_CIRCUIT_DIR / "proof.json"
        submitted = load(CASE_DIRS["tampered_1"] / "artifact.json")["witness"]["q_noisy"]
        # The attack is real: under the client's own vk the proof verifies and its checks look clean.
        self.assertTrue(run_role(self.python_cmd, "verify", FOREIGN_CIRCUIT_DIR, proof_path)["verified"])
        own_statement = decode_public_statement(load(proof_path), load(FOREIGN_CIRCUIT_DIR / "settings.json"))
        self.assertTrue(decide(verified=True, statement=own_statement, submitted_q_noisy=submitted).accepted)

        judgement = judge(proof_path, submitted, self.python_cmd)
        self.assertFalse(judgement.verified)
        self.assertFalse(judgement.decision.accepted)
        self.assertIn("proof did not verify", judgement.decision.reasons)

    def test_failed_proof_with_true_client_flag_is_rejected(self) -> None:
        honest = CASE_DIRS["honest_0"]
        forged = with_shifted_public_coordinate(load(honest / "proof.json"), load(SERVER_DIR / "settings.json"), coordinate=0)
        submitted = list(load(honest / "artifact.json")["witness"]["q_noisy"])
        submitted[0] += 1
        with tempfile.TemporaryDirectory() as tmp:
            proof_path = Path(tmp) / "proof.json"
            proof_path.write_text(json.dumps(forged), encoding="utf-8")
            (Path(tmp) / "summary.json").write_text(json.dumps({"client_reported_verified": True}), encoding="utf-8")
            judgement = judge(proof_path, submitted, self.python_cmd)
        # Every decoded check and the binding pass; only the server's own ezkl.verify rejects it.
        self.assertTrue(judgement.decision.clip_ok and judgement.decision.relation_ok and judgement.decision.binding_ok)
        self.assertFalse(judgement.verified)
        self.assertFalse(judgement.decision.accepted)


if __name__ == "__main__":
    unittest.main()
