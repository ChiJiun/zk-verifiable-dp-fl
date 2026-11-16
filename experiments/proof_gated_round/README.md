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
- `ezkl_client_checks/server_setup/`：伺服器固定的電路、`settings.json`、`network.ezkl`（`vk.key`、`pk.key`、`kzg.srs` 不版控）
- `ezkl_client_checks/client_*/{input.json,witness.json,proof.json,summary.json}`：客戶端以伺服器的電路、pk、SRS 產生的 proof；`summary.json` 的 `client_reported_verified` 只是客戶端自檢，伺服器不讀
- `ezkl_client_checks/attack_foreign_circuit/`、`attack_failed_proof_true_flag/`、`attack_fractional_residual/`：三個拒絕案例的 proof
- `ezkl_client_checks/boundary_adaptive_noise/`、`boundary_arbitrary_magnitude/`：私有噪聲無約束的已知邊界案例（會被接受，刻意保留紀錄）

## 證明陳述與伺服器決策（2026-10-18 審查修正）

審查指出先前版本的缺口：`q_noisy` 放在 EZKL 的私有輸入，公開輸出只有裁剪平方和與關係殘差，而伺服器聚合時另外從 `artifact.json` 讀取向量、並沿用 artifact 內的 `clip_ok`／`relation_ok` 旗標，因此證明並未綁定實際被聚合的向量。現行版本：

- `constraint_model.py` 的檢查模型輸出兩個**公開**張量：`checks = (clip_sum_sq, relation_sum_sq)` 與 `public_q_noisy`；
- `gate.py` 由 `proof.json` 的 `instances`（`ezkl.verify` 實際檢查的公開欄位，而非 prover 寫入的 `pretty_public_inputs`）依 `settings.json` 的 `model_instance_shapes`／`model_output_scales` 解碼成 `(clip_sum_sq, relation_sum_sq, q_noisy)`；
- 接受條件由固定 profile 重算：`verified`、`clip_sum_sq <= 1e8 + 420100`、`relation_sum_sq == 0`、且**提交聚合的向量逐座標等於證明中公開的 `q_noisy`**；artifact 的 check 旗標不再使用；
- 聚合只使用證明中公開的向量。

`test_gate.py` 覆蓋：合法 proof + 替換提交向量（單座標偏移、他人向量、長度不符）必須被拒絕；關係殘差只由公開輸出判定；解碼器與 EZKL 自己的 `rescaled_outputs` 一致；舊格式（陳述不含 `q_noisy`）會被拒絕解碼。`run_actual_proof_gated_round.py` 也對每個被接受的 proof 執行「替換為偏移向量」與「替換為其他 client 向量」的檢查，結果寫入 `statements.json` 與 `summary.md`。

## 伺服器端驗證與信任設定（2026-10-20 審查修正）

前一版的 `verified` 讀自客戶端 pipeline 寫的 `summary.json`，vk、settings、SRS 也由各客戶端自行產生，因此客戶端可以用自己的電路（例如 checks 恆為 0）配自己的 vk 產生「驗證通過」的 proof。現行版本：

- `ezkl_roles.py server-setup` 由伺服器單方匯出檢查電路、以固定 run args 產生 `settings.json`（不以任何客戶端資料 calibrate）、`gen_srs`、`setup`；客戶端只拿到 `network.ezkl`、`pk.key`、`kzg.srs`；
- `server_verifier.judge` 把收到的 `proof.json` 複製一份，以伺服器自己的 vk、settings、SRS 對這一份呼叫 `ezkl.verify`，再用伺服器的 settings 解碼同一份 proof 的 instances，最後交給 `gate.decide`；
- 兩個以實際 EZKL 執行的拒絕案例：客戶端自選電路與 vk（在自己的 vk 下驗證為 True、若信任客戶端設定會被接受，但伺服器驗證為 False）；以及把誠實 proof 的公開 `q_noisy` 改 1 個單位、提交同一向量並宣稱 verified=True（解碼後各項檢查與綁定都通過，只有伺服器的 `ezkl.verify` 會拒絕）。

信任假設：伺服器的 setup 是可信的。`gen_srs` 產生的是本機測試用 SRS，不是公開 ceremony 的 SRS；本實驗以單機模擬三方，部署時應改用公開可信的 SRS，並公布 vk 與 settings 的雜湊（`statements.json` 的 `server_setup.sha256`）。

`ServerVerificationTests` 需要可執行 EZKL 的直譯器（`PROOF_GATED_PYTHON` 或 conda 環境 `zkML`）與本機重新產生的 `server_setup` 金鑰；CI 沒有這些檔案時會 skip。

## 已知邊界：私有噪聲沒有約束（2026-11-16 審查）

檢查電路證明的是「存在私有的 `q_clipped`、`q_noise`，使 `sum(q_clipped^2) <= bound` 且 `q_noisy = q_clipped + q_noise`」。`q_noise` 是私有 witness，既沒有範圍檢查，也沒有綁定種子，所以任何整數 `q_noisy` 都能取 `q_clipped = 0`、`q_noise = q_noisy` 滿足兩個條件。這一關因此只能拒絕**自身 witness 不一致**的客戶端（例如本實驗的篡改客戶端），不限制被聚合更新的幅度。`run_actual_proof_gated_round.py` 以伺服器自己的電路、pk、SRS 產生兩份實際 proof 記錄這個邊界，結果寫在 `statements.json` 的 `known_boundary_cases`：

- `boundary_adaptive_noise`：送出被拒客戶端的同一個 `q_noisy`，只把 `q_noise` 改成 `q_noisy - q_clipped`；
- `boundary_arbitrary_magnitude`：`q_clipped = 0`、`q_noise = q_noisy = ±1,000,000`。

兩者都通過伺服器驗證並被接受。限制更新幅度需要在電路內由秘密種子產生有界噪聲，也就是 Halo2 線。

同一輪也發現私有輸入可帶小數：`q_noise` 某座標加 0.5 會證明出殘差 0.25。原本以 `relation_sum_sq < 0.5` 判斷會接受，現改為要求殘差恰為 0，並以 `attack_fractional_residual` 記錄為拒絕案例。

## 重要說明

- 這一輪會對 3 個 client 分別跑實際的 EZKL constraint proof/check
- 預設會把其中 1 個 client 換成 tampered case
- server 只聚合證明驗證通過、約束成立且與公開陳述一致的 `q_noisy` 更新；約束不限制更新幅度（見上節）
- 這條 EZKL 線的噪聲種子仍是公開的（`gaussian_privacy_accounting/` 的 `epsilon = infinity`），綁定修正不改變這一點
