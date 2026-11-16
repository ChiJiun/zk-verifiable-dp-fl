# discrete-noise accounting — Exact discrete-noise accountant

This experiment supplies the privacy theorem and executable accountant for the
exact centered-binomial sampler implemented by the Halo2 verifiable-randomness circuit.

It deliberately does not substitute a Gaussian RDP formula. The implementation
tracks finite-support failures, composes privacy-loss distributions, rounds
privacy losses upward, adds a numerical guard, and includes the low-bit bias
bound for a uniform Pasta field output.

Run:

```powershell
python experiments/discrete_noise_accounting/centered_binomial_accountant.py
python -m unittest discover -s experiments/discrete_noise_accounting -p "test*.py" -v
```

The ideal mechanism receives an information-theoretic `(epsilon, delta)` result
(`epsilon <= 28.840669` at `delta = 1e-5` for the primary profile). This is an
accounting result for the ideal sampler with a fixed displacement pattern; the
actual Poseidon construction receives only a conditional computational-DP result
under the PRF and unique-context assumptions stated in `formal_dp_theorem.md`, and
a DP proof for the complete protocol transcript (commitments, challenges, proofs,
retries) has not been completed. The primary `d=4`, `k=16`, ten-round profile uses
replacement client-level adjacency and fixed participation. Add/remove
participation privacy is outside the stated guarantee.

## Does the bound depend on the dimension?

```powershell
python experiments/discrete_noise_accounting/fixed_norm_pattern_accounting.py
```

`fixed_norm_pattern_accounting.py` answers the review question about higher
dimension. With the circuit's fixed bound `sum(q^2) <= 4` and entries in
`{-1,0,1}`, every admissible update has at most four non-zero coordinates, so two
replacement-adjacent updates differ in `a <= 4` coordinates by 2 and `b`
coordinates by 1 with `2a + b <= 8`; coordinates that agree leak nothing. The
script composes the scalar PLDs for every feasible `(a, b)` and reports the worst
case, `(4, 0)`: `epsilon <= 28.840669` for 10 rounds and `46.855616` for 20
rounds, independent of `d >= 4`. The earlier statement that 385- or 1,991-
dimensional profiles cannot reach a finite epsilon (`privacy_boundary.py`) assumes
instead that *every* coordinate may move by 2, i.e. that the clip bound grows with
`d`; both envelopes are tabulated in `results/fixed_norm_pattern_accounting.md`.
Neither is a statement about the 385–1,991-dimensional EZKL line, which uses a
different quantisation (`s = 10000`, `(Cs)^2 = 1e8`) and public-seed noise.
