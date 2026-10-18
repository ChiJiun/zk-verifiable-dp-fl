# binary-dataset repeatability Multi-Dataset Repeatability

This experiment repeats the same FL/DP baseline comparison across multiple tabular binary classification datasets.

Datasets:

- Wisconsin Breast Cancer Diagnostic (`sklearn`)
- Pima Indians Diabetes (`OpenML` data id 37)
- German Credit (`OpenML` data id 31)
- Banknote Authentication (`OpenML` data id 1462)
- Spambase (`OpenML` data id 44)
- Tic-Tac-Toe (`OpenML` data id 50)
- Titanic (`OpenML` data id 40945)
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
```

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
- `results/config.json`
- `results/banknote_dp_sweep.csv`
- `results/banknote_dp_sweep_summary.md`
- `results/blood_transfusion_dp_sweep.csv`
- `results/blood_transfusion_dp_sweep_summary.md`
