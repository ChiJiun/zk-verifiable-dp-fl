# proof-gated aggregation Proof-Gated Round Summary

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

Interpretation:
- This experiment runs actual EZKL-backed client checks before aggregation.
- The proof statement is (clip_sum_sq, relation_sum_sq, q_noisy); the server decodes it from proof.json
  instances, re-derives clip/relation from the recommended profile and only aggregates the proven q_noisy.
- A submitted vector that differs from the proven q_noisy is rejected even though the proof verifies,
  so a valid proof cannot be reused to aggregate a different update.
- Local training provenance is still outside the statement (see the threat model).