# NSTC 大專生研究計畫結案整理清單

正式送件正文為 [LaTeX 主檔](final-report/final-report.tex)。報告分開呈現四維 Halo2 原型的證據、公開種子的負面結果，以及高維約束成本。

## 建議題目定位

**基於 ZKML 的聯邦學習 DP-update 可審計原型：可驗證隨機性、Proof-gated Aggregation 與隱私邊界**

一句話核心主張：

> 本研究把固定 profile 的秘密隨機性、離散噪聲取樣、clipping 與 additive relation 整合進 actual Halo2 proof，並展示 proof-gated 多輪聚合；同時以高維壓力測試與攻擊實驗界定此保證不能外推成完整 local-training correctness、任意 poisoning defense 或 production-scale DP-FL。

## 國科會格式與篇幅

依[大專學生研究計畫 FAQ](https://www.nstc.gov.tw/folksonomy/detail/03a84ac2-b906-472d-a73f-3d86f3844024?l=ch)，封面由系統產生，其餘格式參考[國科會 114 年 10 月修正版](https://rd-r.ntust.edu.tw/var/file/55/1055/img/909083360.pdf#page=3)。

- 審閱 PDF 保留封面。若上傳系統會另產生封面，可將主檔的 `\reportcovertrue` 改為 `\reportcoverfalse` 後輸出正文。
- 完整報告不得少於 10 頁，格式未列上限；延後公開時提交的精簡報告以 3–10 頁為原則。
- 順序：目錄、中英文摘要及關鍵詞、前言、研究目的、文獻探討、研究方法、結果與討論、結論與建議、參考文獻。正文交代執行困難；必要的證據索引可放附錄。
- A4、單行行距、中文標楷體、英文 Times New Roman，字體以 12 點為主；目錄與摘要用羅馬數字，正文至附錄用阿拉伯數字。
- 舊版成果彙整表已刪除。若系統有成果貢獻欄，在系統填寫；可推廣的研發成果等條件性表單交由學校確認。

## 正文必放的證據

| 問題 | 結果 | 來源 |
|---|---|---|
| Randomness 是否真的在 circuit 內 | Actual Halo2 tests 8/8 通過，包含 zero-noise、context swap 等拒絕案例 | `experiments/halo2_verifiable_randomness/` |
| 是否有有限 privacy budget | 固定 `d=4, k=16`、10 rounds、replacement-client profile 的理想離散機制：會計結果 `epsilon ≈ 28.84`（`28.840669`）at `delta=1e-5`；實際協定完整 transcript 的 DP 證明尚待完成 | `experiments/discrete_noise_accounting/results/accounting_results.json` |
| 是否連到多輪 FL | 3 clients × 10 rounds × 5 seeds，150/150 proofs 通過並可從磁碟重驗模型鏈 | `experiments/actual_multiround_halo2/results_roundtrip/summary.json` |
| 高維成本是否量測 | 385–1,991 維 actual EZKL constraint proofs；K=50、R=20 training stress test | `experiments/production_scaling/results/` |
| 是否能阻止任意 poisoning | 不能；合法 bounded sign-flip 的 300/300 惡意更新通過（政策模擬，未產生實際證明） | `experiments/robust_aggregation/results/` |
| 結果是否完整 | 核心矩陣完整性、paired effects、環境與 SHA-256 manifest | `experiments/experimental_rigor_audit/results/` |

完整路由見 [`../research/claim-evidence-map.md`](../research/claim-evidence-map.md)。

## 必須保留的負面結果

- 舊 EZKL/public-seed 線讓 verifier 可扣除 noise，因此其 `epsilon = infinity`；這和新的固定 Halo2 hidden-randomness profile 是兩個不同機制。
- `epsilon = 28.84` 仍很大，不能描述成強實務隱私。
- 高維 EZKL/scaling 結果沒有 hidden-randomness theorem，不繼承四維 epsilon。
- 多數 utility 實驗只有 3–5 seeds；沒有 Holm-adjusted statistical significance 時，只寫描述性 effect／可行性。
- Update proof 不驗證資料來源或 optimizer provenance；bounded poisoning 可合法通過。
- 1,440 client decisions 是 policy simulation，1,000-proof workload 是外推，兩者都不是相同數量的 actual proofs。

## 建議圖表

1. 系統時序：commit → challenge → prove → verify → aggregate。
2. 固定四維 Halo2 relation 與 public/private inputs。
3. `epsilon`–accuracy 曲線；目前若沒有 `epsilon=1/4/8` 的 matched baseline，圖說必須標為缺口。
4. 逐更新多輪 proof 數量、prove/verify time 與模型鏈重驗。
5. 385–1,991 維 constraint cost scaling，明示「無此維度的有限 epsilon」。
6. Bounded poisoning 對 mean／median／trimmed mean 的比較與 300/300 acceptance（政策模擬，未產生實際證明）。

## 送件前檢查

- [x] 主張、腳本、raw result 與限制已有單一對照表。
- [x] Actual proof/verify 含 honest 與 fail cases。
- [x] Privacy theorem 的 adjacency、profile、rounds、delta 與假設已列明。
- [x] 大型資料、高維成本、non-IID、攻擊與 robust aggregation 結果均保留。
- [x] AI 協助揭露文字已準備。
- [x] 將報告整理成唯一的送件正文（`final-report/final-report.tex`）。
- [ ] 在送件系統核對自動產生的封面欄位、上傳檔案與校內要求，並請指導教授確認。
- [ ] 親自核對 `final-report/ref.bib` 的每一條文獻（見 `experiment-design-audit.md` F5）。
- [ ] 由作者逐項重跑或抽驗主張—證據表。
- [ ] 決定 repository 授權並加入 `LICENSE`。
