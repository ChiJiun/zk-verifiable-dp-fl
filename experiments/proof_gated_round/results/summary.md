# proof-gated aggregation Proof-Gated Round Summary

- Verification: the server runs ezkl.verify itself with its fixed vk, settings and test SRS
  (ezkl_client_checks/server_setup), then decodes the instances of that same proof.
- Tampered client: 1
- Accepted proofs: 2/3
- Rejected proofs: 1/3
- Tampered client accepted: False
- Accepted aggregate vector length: 10
- Valid proof + single-coordinate shifted submission rejected: 2/2
- Valid proof + other client's vector rejected: 4/4

Accepted clients:
- client 0 (honest_profile): verified=True, clip_ok=True, relation_ok=True, binding_ok=True
- client 2 (honest_profile): verified=True, clip_ok=True, relation_ok=True, binding_ok=True

Rejected clients:
- client 1 (tampered_noisy_profile): verified=True, clip_ok=True, relation_ok=False, binding_ok=True (proven relation residual is non-zero)

Adversarial cases (real EZKL):
- foreign_circuit_and_vk: client_reported_verified=True, verified_under_client_vk=True, accepted_if_client_setup_trusted=True, server_verified=False, clip_ok=True, relation_ok=True, binding_ok=True, accepted=False
- failed_proof_with_true_flag: client_reported_verified=True, server_verified=False, clip_ok=True, relation_ok=True, binding_ok=True, accepted=False

Interpretation:
- This experiment runs actual EZKL-backed client checks before aggregation.
- The server alone fixes the circuit, settings, SRS and keys; clients prove with the server's
  compiled circuit, pk and SRS. The SRS is an ezkl.gen_srs test SRS, so this is a single-machine
  simulation that trusts the server's setup, not a deployment with a ceremony SRS.
- The proof statement is (clip_sum_sq, relation_sum_sq, q_noisy); the server decodes it from the
  instances of the proof it verified, re-derives clip/relation from the recommended profile and only
  aggregates the proven q_noisy.
- A submitted vector that differs from the proven q_noisy is rejected even though the proof verifies,
  so a valid proof cannot be reused to aggregate a different update.
- A proof made under a client's own circuit and vk, or one that fails verification, is rejected
  whatever the client reports about it.
- Local training provenance is still outside the statement (see the threat model).
