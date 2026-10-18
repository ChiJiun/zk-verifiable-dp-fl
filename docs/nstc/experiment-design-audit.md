# 結案前實驗設計與完整性審查

審查日期：2026-10-18。審查對象：GitHub repo（commit `4623db8`）、原提案書（`proposal.tex`、`v2.tex`）、兩份舊結案草稿（`report.tex`、`main.tex`），以及 `docs/research/`、`docs/publication/` 的現行主張文件。判定順序依 [`../README.md`](../README.md)：威脅模型 → 主張—證據對照 → 投稿強化報告 → 個別實驗原始結果。

一句話結論：**實驗量與證據鏈足以結案，且核心主張已有原始結果檔與 CI 佐證；但提案書的資料集、噪聲機制與三個研究問題有明顯改道，結案報告必須逐項交代，而不能沿用 zip 內兩份舊草稿的範圍與措辭。**

## 一、提案承諾與實際完成對照

| 提案項目 | 提案內容 | 實際完成 | 判定 | 結案報告處理 |
|---|---|---|---|---|
| 研究問題一：噪聲生成電路化 | 以 Poseidon PRNG + lookup-table 逆變換取樣產生拉普拉斯噪聲 | Poseidon PRG + canonical 255-bit 分解 + `k=16` centered-binomial 取樣，進入 actual Halo2 circuit（4 維固定 profile） | 達成，但機制改為離散二項式 | 明述改道理由：有限域內可精確取樣、無超越函數、可做 exact accountant；拉普拉斯/指數機制列為未實作 |
| 研究問題二：量化 scale 對 `(epsilon, delta)` 的靈敏度 | 分析 scale 變動是否造成隱私預算衰減 | 有 `scale=8/12/16` 的 accuracy／proving-time sweep、量化 rounding 導致 honest relation 0/9 成立、`4200 ppm` slack、field low-bit bias `5.9e-66`；**沒有** scale 對 epsilon 的系統曲線 | 部分達成 | 以「量化對可驗證性與正確性的影響」回答，並明列 scale→epsilon 曲線為未完成 |
| 研究問題三：邊緣裝置（ARM）效能邊界 | 在 ARM 類邊緣裝置量測 proving time／RAM／proof size | 全部量測在 Intel x86（Windows）與 GitHub Ubuntu／Windows runner；有 prove/verify/RSS/proof size/payload，無 ARM | 部分達成 | 以 x86 CPU 數據代替，ARM 列為限制 |
| 資料集 | MNIST（LeNet-5 CNN）、UCI Heart Disease（MLP） | UCI Adult 主線、11 個二元表格、Iris/Wine/Digits、Forest CoverType 581,012 筆、4 維合成資料；無 MNIST、無 Heart Disease | 改道 | 說明 CNN 在 ZK 內成本與審查人要求更多資料集；Heart Disease 可用既有 pipeline 低成本補跑（見第六節） |
| 證明本地訓練（梯度計算）正確性 | 對「梯度計算」與「加噪過程」生成證明 | 只證明 clipping bound、additive relation、hidden randomness；bounded sign-flip 300/300 通過 gate | 未達成，明示 out of scope | 必須寫入限制；不能沿用提案的「證明本地訓練正確」措辭 |
| 效能預期 | Heart Disease MLP 證明 `<10 s`、`<1 GB` | 所有單一 proof `<2 s`、peak RSS `<480 MiB`（EZKL 15–1,991 維；Halo2 4 維） | 數值達標但模型不同 | 如實標明模型與資料不同 |
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

## 四、結案報告採用的主張措辭

可主張（逐條有原始檔）：

1. 裁剪與加性噪聲關係可轉為 canonical quantized witness + fixed slack 的 ZKML 可審計條件；推薦 profile 下 honest 9/9 通過、tampered 18/18 拒絕；actual EZKL 在 15–1,991 維完整更新向量上均能拒絕偏移 1 單位的篡改。
2. Proof 結果可控制聚合：單輪 2/3 接受並回寫模型；4 維 Halo2 線 3 clients × 10 rounds × 5 seeds，150/150 actual proofs、150/150 磁碟重驗、1,050/1,050 負面 probe 拒絕。
3. Hidden randomness 已進 actual Halo2 circuit；固定 `d=4, k=16, 10 rounds` 的 exact PLD accountant 給出 `epsilon <= 28.840669` at `delta = 1e-5`（replacement client-level，ideal sampler；Poseidon 版為 PRF 假設下的 computational DP）。
4. 效用與成本已跨 16 個資料集、581,012 筆 CoverType、K=3/10/25/50、R 最多 20、IID／Dirichlet partition 量測；proof 成本隨維度成長（15→650 維 proving time 5.86 倍、proving key 28.4 倍）。
5. 負面結果：public seed `epsilon = infinity`；replay／zero-noise 需 context 與 noise policy；bounded sign-flip 100% 通過 gate，median／trimmed mean 只部分緩解（retention gain 0.1988／0.1541，`p = 0.001953`）。

不可主張：完整 local-training correctness、任意 poisoning 防禦、高維模型的有限 epsilon、production 部署效能、統計顯著（robust aggregation 除外）。

## 五、新結案報告的結構

依國科會大專生研究計畫成果報告慣用格式：封面、中英文摘要、目錄、一前言、二研究目的、三文獻探討、四研究方法、五結果與討論、六結論與建議（含成果自評與提案對照）、參考文獻、附錄（主張—證據—檔案對照、重現指令）。LaTeX 來源在 [`final-report/final-report.tex`](final-report/final-report.tex)，圖檔由 `experiments/*/results/` 複製到 `final-report/figures/`。

## 六、投稿前建議補做的實驗（依證據缺口排序）

1. **Mixed accepted／rejected 多輪 live run**：每輪加入一個惡意提交並消耗 ticket，量測 cohort 大小、效用與 availability（`experiments/actual_multiround_halo2/NEXT_EXPERIMENTS.md` 第 1 項）。
2. **真實資料 4 維實驗**：預先宣告公開特徵子集與量化，用相同電路 profile 比較 no-noise／noisy-no-proof／actual-proof。UCI Heart Disease 可作為此實驗或二元 pipeline 的補跑資料集，以回應提案承諾。
3. **Natural-client benchmark 與 partial participation／dropout**（FEMNIST／FedScale split）。
4. **Matched epsilon–utility 對照**：在 `epsilon = 1/4/8` 下與 FL／clip-only 比較；目前只有條件式 Gaussian frontier。
5. **形式化安全分析**：commitment hiding、PRF-to-DP hybrid、adaptive composition（dominating pair）、selective abort／collusion；由第三方審查 circuit relation。
6. **高維 hidden-randomness circuit**：先定義 adjacency、update envelope、noise unit 與目標 budget；`k=16` 直接外推到 385／1,991 維會跌破 delta floor。
7. **ARM／邊緣裝置量測**與 **key reuse／parallel proving** 受控比較，回應提案研究問題三與 1,000-proof 外推。

## 七、送件前作者自查

- [ ] 逐條重跑或抽驗附錄 A 的主張—證據對照（至少 `check_repository.py`、accountant 與 Halo2 測試、一個 seed 的多輪實驗）。
- [ ] 親自核對參考文獻（特別是 F5 列出的條目）。
- [ ] 填入計畫編號、執行期間、指導教授與系所。
- [ ] 決定是否補跑 Heart Disease；若不補，保留第一節的改道說明。
- [ ] 依 [`../governance/ai-assistance.md`](../governance/ai-assistance.md) 放入 AI 協助揭露。
- [ ] 決定 repository 授權並加入 `LICENSE`。
