# Fixed-L2-bound pattern accounting (k=16, delta=1e-05)

If `sum(q_clip^2) <= 4` with entries in {-1,0,1} is kept in any dimension d >= 4, two
replacement-adjacent updates differ in at most `a <= 4` coordinates by 2 and `b` coordinates
by 1 with `2a + b <= 8`. The tables list the composed epsilon upper bound for every feasible
pattern; the worst case is a dimension-free bound for the fixed-bound mechanism.

## Fixed bound, 10 rounds

| a (shift 2) | b (shift 1) | compositions | epsilon upper | delta floor |
|---:|---:|---:|---:|---:|
| 0 | 1 | 0x2 + 10x1 | 5.099154 | 2.328e-09 |
| 0 | 2 | 0x2 + 20x1 | 7.625340 | 4.657e-09 |
| 0 | 3 | 0x2 + 30x1 | 9.728969 | 6.985e-09 |
| 0 | 4 | 0x2 + 40x1 | 11.609682 | 9.313e-09 |
| 0 | 5 | 0x2 + 50x1 | 13.346533 | 1.164e-08 |
| 0 | 6 | 0x2 + 60x1 | 14.980515 | 1.397e-08 |
| 0 | 7 | 0x2 + 70x1 | 16.536176 | 1.630e-08 |
| 0 | 8 | 0x2 + 80x1 | 18.029602 | 1.863e-08 |
| 1 | 0 | 10x2 + 0x1 | 11.860677 | 7.683e-08 |
| 1 | 1 | 10x2 + 10x1 | 13.540976 | 7.916e-08 |
| 1 | 2 | 10x2 + 20x1 | 15.138205 | 8.149e-08 |
| 1 | 3 | 10x2 + 30x1 | 16.668213 | 8.382e-08 |
| 1 | 4 | 10x2 + 40x1 | 18.142807 | 8.615e-08 |
| 1 | 5 | 10x2 + 50x1 | 19.570853 | 8.848e-08 |
| 1 | 6 | 10x2 + 60x1 | 20.959156 | 9.080e-08 |
| 2 | 0 | 20x2 + 0x1 | 18.251399 | 1.537e-07 |
| 2 | 1 | 20x2 + 10x1 | 19.666360 | 1.560e-07 |
| 2 | 2 | 20x2 + 20x1 | 21.044222 | 1.583e-07 |
| 2 | 3 | 20x2 + 30x1 | 22.389610 | 1.607e-07 |
| 2 | 4 | 20x2 + 40x1 | 23.706308 | 1.630e-07 |
| 3 | 0 | 30x2 + 0x1 | 23.774427 | 2.305e-07 |
| 3 | 1 | 30x2 + 10x1 | 25.059911 | 2.328e-07 |
| 3 | 2 | 30x2 + 20x1 | 26.323262 | 2.352e-07 |
| 4 | 0 | 40x2 + 0x1 | 28.840669 | 3.073e-07 |

Worst case: a=4, b=0, epsilon <= 28.840669.

## Fixed bound, 20 rounds

| a (shift 2) | b (shift 1) | compositions | epsilon upper | delta floor |
|---:|---:|---:|---:|---:|
| 0 | 1 | 0x2 + 20x1 | 7.625340 | 4.657e-09 |
| 0 | 2 | 0x2 + 40x1 | 11.609682 | 9.313e-09 |
| 0 | 3 | 0x2 + 60x1 | 14.980515 | 1.397e-08 |
| 0 | 4 | 0x2 + 80x1 | 18.029602 | 1.863e-08 |
| 0 | 5 | 0x2 + 100x1 | 20.871611 | 2.328e-08 |
| 0 | 6 | 0x2 + 120x1 | 23.565830 | 2.794e-08 |
| 0 | 7 | 0x2 + 140x1 | 26.147676 | 3.260e-08 |
| 0 | 8 | 0x2 + 160x1 | 28.640319 | 3.725e-08 |
| 1 | 0 | 20x2 + 0x1 | 18.251399 | 1.537e-07 |
| 1 | 1 | 20x2 + 20x1 | 21.044222 | 1.583e-07 |
| 1 | 2 | 20x2 + 40x1 | 23.706308 | 1.630e-07 |
| 1 | 3 | 20x2 + 60x1 | 26.265641 | 1.676e-07 |
| 1 | 4 | 20x2 + 80x1 | 28.741705 | 1.723e-07 |
| 1 | 5 | 20x2 + 100x1 | 31.148618 | 1.770e-07 |
| 1 | 6 | 20x2 + 120x1 | 33.496965 | 1.816e-07 |
| 2 | 0 | 40x2 + 0x1 | 28.840669 | 3.073e-07 |
| 2 | 1 | 40x2 + 20x1 | 31.235654 | 3.120e-07 |
| 2 | 2 | 40x2 + 40x1 | 33.574517 | 3.166e-07 |
| 2 | 3 | 40x2 + 60x1 | 35.864769 | 3.213e-07 |
| 2 | 4 | 40x2 + 80x1 | 38.112403 | 3.260e-07 |
| 3 | 0 | 60x2 + 0x1 | 38.175365 | 4.610e-07 |
| 3 | 1 | 60x2 + 20x1 | 40.380141 | 4.657e-07 |
| 3 | 2 | 60x2 + 40x1 | 42.551963 | 4.703e-07 |
| 4 | 0 | 80x2 + 0x1 | 46.855616 | 6.147e-07 |

Worst case: a=4, b=0, epsilon <= 46.855616.

## Full-displacement envelope (every coordinate may move by 2, i.e. C_q^2 = d)

| d | rounds | compositions | delta floor | field bias | epsilon upper |
|---:|---:|---:|---:|---:|---:|
| 4 | 10 | 40 | 3.073e-07 | 5.9e-66 | 28.840669 |
| 385 | 10 | 3850 | 2.958e-05 | 5.7e-64 | none (delta floor above target) |
| 1991 | 10 | 19910 | 1.530e-04 | 3.0e-63 | none (delta floor above target) |
| 385 | 20 | 7700 | 5.916e-05 | 1.1e-63 | none (delta floor above target) |
| 1991 | 20 | 39820 | 3.059e-04 | 5.9e-63 | none (delta floor above target) |

Scope: ideal independent centered-binomial noise, fixed non-adaptive displacement pattern per round, replacement client-level adjacency; not a statement about the full ZK transcript
