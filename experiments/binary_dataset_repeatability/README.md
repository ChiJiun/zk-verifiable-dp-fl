# binary-dataset repeatability Multi-Dataset Repeatability

This experiment repeats the same FL/DP baseline comparison across multiple tabular binary classification datasets.

Datasets:

- Wisconsin Breast Cancer Diagnostic (`sklearn`)
- Pima Indians Diabetes (`OpenML` data id 37)
- German Credit (`OpenML` data id 31)
- Banknote Authentication (`OpenML` data id 1462)
- Spambase (`OpenML` data id 44)
- Tic-Tac-Toe (`OpenML` data id 50)
- Titanic (`OpenML` data id 40945). The `boat` (lifeboat) and `body` (body identification number) columns are recorded after the outcome and encode survival almost directly, so they are dropped before any split or fitting (see the column notes at https://hbiostat.org/r/rms/examples). The first recorded run used every input column; after the 2026-10-18 review the dataset was re-run without the two leakage columns and only those rows were replaced (FL 0.821883 -> 0.755725, DP 0.790076 -> 0.739186, retention 0.961300 -> 0.978114). `name`, `ticket`, `cabin` and `home.dest` are still one-hot encoded as before.
- ILPD (`OpenML` data id 1480)
- PC4 (`OpenML` data id 1049)
- Blood Transfusion Service Center (`OpenML` data id 1464)
- KC2 (`OpenML` data id 1063)
- UCI Heart Disease, Cleveland subset (`OpenML` data id 49, `heart-c`; 303 rows, target binarised to presence/absence of heart disease). Added after the other eleven to cover the dataset promised in the original NSTC proposal.

All datasets share one preprocessing path: median imputation + standardisation for numeric columns, most-frequent imputation + one-hot encoding for categorical columns, with every transformer fitted on the training split only (80/20 stratified split per seed).

## Run

```powershell
python experiments/binary_dataset_repeatability/run_multi_dataset_repeats.py
```

Add or re-run a single dataset without touching the recorded rows of the others (this is how `heart_disease` was added; the summary files are recomputed over all merged rows):

```powershell
python experiments/binary_dataset_repeatability/run_multi_dataset_repeats.py --datasets heart_disease --merge-existing
python experiments/binary_dataset_repeatability/run_multi_dataset_repeats.py --datasets titanic --merge-existing
```

`--output-dir <dir>` writes the four result files somewhere else (for example to compare a re-run against the recorded rows before replacing them); `--merge-existing` always reads the recorded rows from `results/multi_dataset_runs.csv`. Re-running `breast_cancer_wisconsin` with the recorded defaults reproduced all six recorded rows exactly on the machine used for the Titanic re-run (torch 2.9.1+cpu, scikit-learn 1.4.2).

Run the banknote-specific DP parameter sweep:

```powershell
python experiments/binary_dataset_repeatability/run_banknote_dp_sweep.py
```

Run the blood-transfusion-specific DP parameter sweep:

```powershell
python experiments/binary_dataset_repeatability/run_blood_transfusion_dp_sweep.py
```

## Outputs

- `results/multi_dataset_runs.csv`
- `results/multi_dataset_summary.csv`
- `results/summary.md`
- `results/config.json` (includes `dropped_columns` per dataset)
- `results/banknote_dp_sweep.csv`
- `results/banknote_dp_sweep_summary.md`
- `results/blood_transfusion_dp_sweep.csv`
- `results/blood_transfusion_dp_sweep_summary.md`
