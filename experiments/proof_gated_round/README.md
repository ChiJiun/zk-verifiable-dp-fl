# proof-gated aggregation - Proof-Gated Round

proof-gated aggregation 的目標是讓每個 client update 先通過 actual EZKL-backed constraint check，再由 server 聚合通過者。

## 執行方式

```bash
python experiments/proof_gated_round/run_actual_proof_gated_round.py
```

預設以 `conda run -n zkML python` 執行 EZKL 子流程；可用 `--python <interpreter>` 或環境變數 `PROOF_GATED_PYTHON` 指定任一安裝了 `torch` 與 `ezkl` 的直譯器。主程序只需標準函式庫。

伺服器端 gate 的單元測試（不需要 EZKL；若 `ezkl_client_checks/*/proof.json` 存在，也會對實際錄下的 proof 檢查綁定）：

```bash
python -m unittest discover -s experiments/proof_gated_round -p "test*.py" -v
```

## 輸出

- `results/proof_gated_round.csv`（含 `binding_ok`、`shifted_vector_rejected`）
- `results/statements.json`（每個 client 由 proof 解碼的公開陳述、提交向量、決策，以及跨 client 的替換向量測試）
- `results/accepted_aggregate.json`
- `results/summary.md`
- `ezkl_client_checks/client_*/{proof.json,settings.json,summary.json}`（`*.key`、`*.srs` 不版控）

## 證明陳述與伺服器決策（2026-10-18 審查修正）

審查指出先前版本的缺口：`q_noisy` 放在 EZKL 的私有輸入，公開輸出只有裁剪平方和與關係殘差，而伺服器聚合時另外從 `artifact.json` 讀取向量、並沿用 artifact 內的 `clip_ok`／`relation_ok` 旗標，因此證明並未綁定實際被聚合的向量。現行版本：

- `constraint_model.py` 的檢查模型輸出兩個**公開**張量：`checks = (clip_sum_sq, relation_sum_sq)` 與 `public_q_noisy`；
- `gate.py` 由 `proof.json` 的 `instances`（`ezkl.verify` 實際檢查的公開欄位，而非 prover 寫入的 `pretty_public_inputs`）依 `settings.json` 的 `model_instance_shapes`／`model_output_scales` 解碼成 `(clip_sum_sq, relation_sum_sq, q_noisy)`；
- 接受條件由固定 profile 重算：`verified`、`clip_sum_sq <= 1e8 + 420100`、`relation_sum_sq == 0`、且**提交聚合的向量逐座標等於證明中公開的 `q_noisy`**；artifact 的 check 旗標不再使用；
- 聚合只使用證明中公開的向量。

`test_gate.py` 覆蓋：合法 proof + 替換提交向量（單座標偏移、他人向量、長度不符）必須被拒絕；關係殘差只由公開輸出判定；解碼器與 EZKL 自己的 `rescaled_outputs` 一致；舊格式（陳述不含 `q_noisy`）會被拒絕解碼。`run_actual_proof_gated_round.py` 也對每個被接受的 proof 執行「替換為偏移向量」與「替換為其他 client 向量」的檢查，結果寫入 `statements.json` 與 `summary.md`。

## 重要說明

- 這一輪會對 3 個 client 分別跑實際的 EZKL constraint proof/check
- 預設會把其中 1 個 client 換成 tampered case
- server 只聚合證明驗證通過、約束成立且與公開陳述一致的 `q_noisy` 更新
- 這條 EZKL 線的噪聲種子仍是公開的（`gaussian_privacy_accounting/` 的 `epsilon = infinity`），綁定修正不改變這一點
