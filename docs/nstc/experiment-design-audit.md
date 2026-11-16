# 結案前實驗設計與完整性審查

審查日期：2026-10-18。審查對象：GitHub repo（commit `4623db8`）、原提案書（`proposal.tex`、`v2.tex`）、兩份舊結案草稿（`report.tex`、`main.tex`），以及 `docs/research/`、`docs/publication/` 的現行主張文件。判定順序依 [`../README.md`](../README.md)：威脅模型 → 主張—證據對照 → 投稿強化報告 → 個別實驗原始結果。

一句話結論：**實驗量與證據鏈足以結案，且核心主張已有原始結果檔與 CI 佐證；但提案書的資料集、噪聲機制與三個研究問題有明顯改道，結案報告必須逐項交代，而不能沿用 zip 內兩份舊草稿的範圍與措辭。**

## 一、提案承諾與實際完成對照

| 提案項目 | 提案內容 | 實際完成 | 判定 | 結案報告處理 |
|---|---|---|---|---|
| 研究問題一：噪聲生成電路化 | 以 Poseidon PRNG + lookup-table 逆變換取樣產生拉普拉斯噪聲 | Poseidon PRG + canonical 255-bit 分解 + `k=16` centered-binomial 取樣，進入 actual Halo2 circuit（4 維固定 profile） | 達成，但機制改為離散二項式 | 明述改道理由：有限域內可精確取樣、無超越函數、可做 exact accountant；拉普拉斯/指數機制列為未實作 |
| 研究問題二：量化 scale 對 `(epsilon, delta)` 的靈敏度 | 分析 scale 變動是否造成隱私預算衰減 | 有 `scale=8/12/16` 的 accuracy／proving-time sweep、量化 rounding 導致 honest relation 0/9 成立、`4200 ppm` slack、field low-bit bias `5.9e-66`；**沒有** scale 對 epsilon 的系統曲線 | 部分達成 | 以「量化對可驗證性與正確性的影響」回答，並明列 scale→epsilon 曲線為未完成 |
| 研究問題三：邊緣裝置（ARM）效能邊界 | 在 ARM 類邊緣裝置量測 proving time／RAM／proof size | 全部量測在 Intel x86（Windows）與 GitHub Ubuntu／Windows runner；有 prove/verify/RSS/proof size/payload，無 ARM | 部分達成 | 以 x86 CPU 數據代替，ARM 列為限制 |
| 資料集 | MNIST（LeNet-5 CNN）、UCI Heart Disease（MLP） | UCI Adult 主線、12 個二元表格（含 2026-10-18 以既有 pipeline 補跑的 UCI Heart Disease Cleveland 303 筆，線性模型，3 seeds × FL/DP；保留率 0.830882，未達 90% 門檻，未調參）、Iris/Wine/Digits、Forest CoverType 581,012 筆、4 維合成資料；無 MNIST | 部分改道（Heart Disease 已補跑，但模型為線性而非 MLP） | 說明 CNN 在 ZK 內成本與審查人要求更多資料集；Heart Disease 結果如實列入表 3 與正文（`experiments/binary_dataset_repeatability/results/multi_dataset_summary.csv`） |
| 證明本地訓練（梯度計算）正確性 | 對「梯度計算」與「加噪過程」生成證明 | 只證明 clipping bound、additive relation、hidden randomness；bounded sign-flip 300/300 通過 gate | 未達成，明示 out of scope | 必須寫入限制；不能沿用提案的「證明本地訓練正確」措辭 |
| 效能預期 | Heart Disease MLP 證明 `<10 s`、`<1 GB` | Halo2 4 維 150 份逐更新 proof 平均 1.952 s、最大 3.994 s（60 份 > 2 s）；EZKL 1,991 維平均 1.658 s、最大 1.858 s；peak RSS `<480 MiB` | 低於 10 s 門檻，但模型不同；「所有單一 proof < 2 s」與原始 `run.json` 不符，已更正 | 如實標明模型與資料不同，並以原始 `seed_*/run.json` 的 `prove_seconds` 為準 |
| 硬體 | NVIDIA GPU 工作站 | 純 CPU | 改道 | 註明 |
| 框架 | EZKL 為主 | EZKL（KZG）+ Zcash Halo2（IPA）兩個 backend | 超出提案 | 說明兩者 circuit 不同，不做 head-to-head |

## 二、實驗設計是否足以回答核心問題

核心問題：DP 更新中的裁剪與加噪能否轉成 ZK 可審計條件，並控制聚合。

- **對照設計正確**。S0/S1/S2 共用 seed、split、partition、初始化與 shuffle；CoverType 線另有 clipping-only control，可分解 clipping 與 noise 的效用損失。
- **誠實／篡改案例設計正確**。每個 constraint 實驗都有 honest 與 tampered（偏移 1 個量化單位）兩類；Halo2 線另有 zero-noise、context swap、replay、corrupt proof 等 7 種 probe。
- **兩條實驗線必須分開呈現**（[`../research/threat-model.md`](../research/threat-model.md)）：固定 4 維 Halo2 hidden-randomness 線有有限 epsilon；385–1,991 維 EZKL constraint-only 線沒有 hidden randomness，舊 public-seed 機制 `epsilon = infinity`。任何表格或摘要都不能寫成「高維且 `epsilon <= 28.84`」。
- **統計設計的限制已被量化**。3–5 seeds 下 exact sign-flip 最小 p 為 0.25／0.0625，Holm 校正後 0 組顯著；只有 robust aggregation（10 seeds）的 `p = 0.001953` 可稱顯著。結案報告只能用「支持／顯示／在本實驗範圍內」。
- **非 actual proof 的數字已標示**：1,440 決策是 policy simulation；1,000-proof workload 是外推；Control B 是算術等價檢查。

## 三、完整性與一致性問題（具體發現）

| 編號 | 發現 | 位置 | 處理 |
|---|---|---|---|
| F1 | zip 內 `report.tex` 與 `main.tex` 完全未涵蓋 Halo2 電路、exact accountant、CoverType、non-IID、威脅矩陣、robust aggregation、多輪 150 proofs；`main.tex` 摘要「本研究證明……」措辭過強 | zip | 新結案報告（`final-report/`）重寫，不以舊稿為底 |
| F2 | Halo2 測試數量不一致：README／roadmap 寫 8/8，strengthening-report 寫 4/4 | `docs/publication/strengthening-report.md` | 實際為 `main.rs` 4 個電路測試 + `federated.rs` 4 個聯邦整合測試，報告統一寫「8（4 電路 + 4 整合）」 |
| F3 | 同一 4 維 profile 有兩個 epsilon：PLD `28.840669` 與 basic composition `195.852561` | `discrete_noise_accounting/`、`actual_multiround_halo2/privacy_results/` | 報告需解釋：PLD 是理想機制的 tight 上界；basic composition 是保守診斷；兩者都不是完整 transcript 的 DP 證明 |
| F4 | `multiclass_repeatability/results/summary.md` 寫「尚未對這些新資料集產生完整 EZKL 證明」，但 `multiclass_vdp_zk` 與 `zk_cost_scaling` 已完成 | 該 summary | 文件過時；結案報告以 `zk_cost_scaling` 結果為準 |
| F5 | `ref.bib` 的 `costello2020halo` 作者與題名不符：題名「Recursive Proof Composition without a Trusted Setup」是 Bowe–Grigg–Hopwood 的 Halo（ePrint 2019/1021），作者欄卻寫 Costello；`zhang2021zkcnn` 作者有誤（zkCNN 為 Liu–Xie–Zhang, CCS 2021）；`mcmahan2017communication` 與 `mcmahan2017fedavg` 重複；`main.tex` 將 Ahmed 等人的 ICIMIA 論文稱為「Shakeb 等人」 | zip `ref.bib`、`main.tex` | 新報告重建 `ref.bib`；`tolpegin2023poisoning`（arXiv 2310.14848）與 ICIMIA 論文作者請作者親自核對 |
| F6 | 合成資料多輪 Halo2 的 noisy proof-gated 準確率 `0.8309 ± 0.0989`，seed 62 只有 `0.707`；無噪聲對照 `0.9441` | `actual_multiround_halo2/results_roundtrip/` | 如實呈現，解讀為 `k=16` 噪聲對 ±1 量化 4 維更新的效用代價 |
| F7 | 威脅矩陣中 zero-noise／clip-bypass 在 ungated 下 retention `>1` | `multiround_threat_matrix/` | 需解釋：移除噪聲或放大更新會提高準確率，所以「準確率上升」不能當作安全訊號 |
| F8 | `results/seed_42` pilot 曾因 JSON 浮點 round-trip 差 1 ULP 導致模型鏈重驗失敗 | `actual_multiround_halo2/results/pilot_failure.json` | 已修正並保留失敗紀錄；報告應保留此負面過程 |
| F9 | Repository 無 `LICENSE` | 根目錄 | 作者決定授權後再加入；結案報告不受影響 |
| F10 | CI 最近一次（2026-10-05，run `37257413993`）Ubuntu／Windows 均通過 | GitHub Actions | 可在報告引用為獨立環境重現證據 |
| F11 | 舊草稿 `report.tex` 指定字型 `AR PL KaitiM Big5`，本機與多數 Windows 無此字型 | zip | 新報告改用 TW-Kai → 標楷體（DFKai-SB）→ Noto Serif TC 的 fallback 鏈 |
| R1 | （外部審查 2026-10-18）EZKL 線 `q_noisy` 在私有輸入，聚合時另從 artifact 讀向量與 check flags，證明未綁定實際聚合的向量 | `proof_gated_round/run_actual_proof_gated_round.py` | 檢查模型新增公開輸出 `public_q_noisy`；`gate.py` 由 proof instances 解碼陳述、重算 clip／relation、要求提交向量等於證明向量；`test_gate.py` 覆蓋「合法 proof + 替換向量 → 拒絕」；EZKL 三個 client 已重跑 |
| R2 | （外部審查）摘要與結論把理想機制的 `epsilon <= 28.84` 寫成實際系統的完整保證 | `final-report.tex` 摘要、§4.5、§5.5、§6.1 | 統一改為「理想離散機制的會計結果為 epsilon 約 28.84；實際協定的完整 computational-DP 證明尚待完成」 |
| R3 | （外部審查）Titanic 使用 OpenML 40945 全部欄位，含結果洩漏欄位 `boat`、`body` | `binary_dataset_repeatability/` | 刪除兩欄重跑（其餘設定不變）：FL 0.755725、DP 0.739186、保留率 0.978114，仍達標；表 9 與摘要列更新 |
| R4 | （外部審查）公開 commit `4623db8` 無 Heart Disease 程式與結果 | `binary_dataset_repeatability/` | 程式與結果自 commit `bf2dd27` 起在 `docs/nstc-final-report` 分支；報告附錄 A 標明 commit |
| R5 | （外部審查）Nasr et al. 2023 被反向引用為「審計需要數千次訓練」 | `final-report.tex` §1、§3.2 | 改述為該文把緊審計降為兩次訓練，保留「統計審計無法逐次判定協定執行」的論點 |
| R6 | （外部審查）高維「無法取得有限 epsilon」未說明假設；固定 `sum(q^2)<=4` 下每向量最多 4 個非零座標，不可能全部座標位移 2 | `discrete_noise_accounting/`、`final-report.tex` §5.5 | 新增 `fixed_norm_pattern_accounting.py`：固定上界下最壞 pattern `(4,0)`，epsilon 與維度無關（10 輪 28.840669、20 輪 46.855616）；原外推改述為「上界隨 d 放寬到每座標位移 2」的假設 |
| R7 | （外部審查）「所有單一證明 < 2 s」與 `run.json` 不符（60/150 > 2 s，最大 3.994 s） | `final-report.tex` 表 13、本文件 | 改為「平均 1.952 s、最大 3.994 s」，仍低於 10 s 門檻 |
| R8 | （外部審查小修）文獻 [11] 第二作者、卷期頁碼；封面佔位符；附錄 B 指令的 U+2010 連字號 | `ref.bib`、`final-report.tex` | 文獻改為 Bontekoe, Asghar, Turkmen, PoPETs 2025(2):543–563；連字號問題來自 XeTeX 字型 ToUnicode，已以 `\XeTeXgenerateactualtext=1` 修正；封面欄位待作者提供 |

## 四、結案報告採用的主張措辭

可主張（逐條有原始檔）：

1. 裁剪與加性噪聲關係可轉為 canonical quantized witness + fixed slack 的 ZKML 可審計條件；推薦 profile 下 honest 9/9 通過、tampered 18/18 拒絕；actual EZKL 在 15–1,991 維完整更新向量上均能拒絕偏移 1 單位的篡改。
2. Proof 結果可控制聚合：單輪 2/3 接受並回寫模型；4 維 Halo2 線 3 clients × 10 rounds × 5 seeds，150/150 actual proofs、150/150 磁碟重驗、1,050/1,050 負面 probe 拒絕。
3. Hidden randomness 已進 actual Halo2 circuit；固定 `d=4, k=16, 10 rounds` 的**理想離散機制**，exact PLD 會計結果為 `epsilon ≈ 28.84` at `delta = 1e-5`（replacement client-level，ideal sampler）。實際協定完整 transcript 的 computational-DP 證明尚待完成；Poseidon 版的結論依賴 PRF 假設。
4. 效用與成本已跨 17 個資料集（含補跑的 Heart Disease）、581,012 筆 CoverType、K=3/10/25/50、R 最多 20、IID／Dirichlet partition 量測；proof 成本隨維度成長（15→650 維 proving time 5.86 倍、proving key 28.4 倍）。
5. 負面結果：public seed `epsilon = infinity`；replay／zero-noise 需 context 與 noise policy；bounded sign-flip 100% 通過 gate，median／trimmed mean 只部分緩解（retention gain 0.1988／0.1541，`p = 0.001953`）。

不可主張：完整 local-training correctness、任意 poisoning 防禦、高維模型的有限 epsilon、production 部署效能、統計顯著（robust aggregation 除外）。

## 五、新結案報告的結構

依國科會大專生研究計畫成果報告慣用格式：封面、中英文摘要、目錄、一前言、二研究目的、三文獻探討、四研究方法、五結果與討論、六結論與建議（含成果自評與提案對照）、參考文獻、附錄（主張—證據—檔案對照、重現指令）。LaTeX 來源在 [`final-report/final-report.tex`](final-report/final-report.tex)，圖檔由 `experiments/*/results/` 複製到 `final-report/figures/`。

## 六、投稿前建議補做的實驗（依證據缺口排序）

1. **Mixed accepted／rejected 多輪 live run**：每輪加入一個惡意提交並消耗 ticket，量測 cohort 大小、效用與 availability（`experiments/actual_multiround_halo2/NEXT_EXPERIMENTS.md` 第 1 項）。
2. **真實資料 4 維實驗**：預先宣告公開特徵子集與量化，用相同電路 profile 比較 no-noise／noisy-no-proof／actual-proof。UCI Heart Disease 已於 2026-10-18 以二元 pipeline 補跑（線性模型，保留率 0.830882，未達標），但尚未進入此四維電路實驗。
3. **Natural-client benchmark 與 partial participation／dropout**（FEMNIST／FedScale split）。
4. **Matched epsilon–utility 對照**：在 `epsilon = 1/4/8` 下與 FL／clip-only 比較；目前只有條件式 Gaussian frontier。
5. **形式化安全分析**：commitment hiding、PRF-to-DP hybrid、adaptive composition（dominating pair）、selective abort／collusion；由第三方審查 circuit relation。
6. **高維 hidden-randomness circuit**：先定義 adjacency、update envelope、noise unit 與目標 budget。若維持 `sum(q^2) <= 4` 的固定上界，有限 epsilon 與維度無關（`fixed_norm_pattern_accounting.py`），但每輪只有 4 個 ±1 座標；若放寬到每座標皆可位移 2，`k=16` 在 385／1,991 維會跌破 delta floor。兩者之間的更新範圍與裁剪上界選擇是待做的設計工作。
7. **ARM／邊緣裝置量測**與 **key reuse／parallel proving** 受控比較，回應提案研究問題三與 1,000-proof 外推。

## 七、送件前作者自查

- [ ] 逐條重跑或抽驗附錄 A 的主張—證據對照（至少 `check_repository.py`、accountant 與 Halo2 測試、一個 seed 的多輪實驗）。
- [ ] 親自核對參考文獻（特別是 F5 列出的條目）。
- [ ] 填入計畫編號、執行期間、指導教授與系所。
- [x] 補跑 Heart Disease（2026-10-18，`run_multi_dataset_repeats.py --datasets heart_disease --merge-existing`）；第一節與結案報告表 3 已更新。
- [x] Titanic 去除 `boat`、`body` 後重跑（2026-10-18，`run_multi_dataset_repeats.py --datasets titanic --merge-existing`）。
- [x] EZKL 證明閘公開 `q_noisy` 綁定與拒絕測試（R1）；三個 client 以 EZKL 10.2.7 重跑。
- [ ] 依 [`../governance/ai-assistance.md`](../governance/ai-assistance.md) 放入 AI 協助揭露。
- [ ] 決定 repository 授權並加入 `LICENSE`。
