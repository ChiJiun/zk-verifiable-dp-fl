# 結案報告交付審查（2026-10-20）

審查對象：分支 `docs/nstc-final-report`，本機 HEAD `5e6885b`（前一個 commit `564c3f4`，兩者未 push；遠端分支停在 `d970126`，遠端 `main` 停在 `4623db8`）。報告為 `docs/nstc/final-report/final-report.tex`、`ref.bib`、`final-report.pdf`（32 頁）。

審查方式：獨立 session，不沿用前一輪修改者的結論。報告全文由本 session 逐行讀過；六個方向（EZKL 綁定、隱私會計、資料集重跑、數字一致性、參考文獻、投稿 venue）各由一個獨立 agent 以程式、原始結果檔與實際執行驗證，關鍵發現再由本 session 抽查原始碼與官方網頁。全程唯讀，所有重跑輸出都在 session scratchpad，repo 只新增本檔（未 commit）。

## 判定

**交付前需修正。** 最重要的三個理由：

1. **報告引用的修訂在公開 repo 上看不到。** 附錄 A（tex 658 行）引用的 `564c3f4` 尚未 push；封面網址指向 repo 首頁，而 GitHub 預設分支 `main` 仍是 `4623db8`，裡面只有 11 個資料集，Titanic 仍含 boat、body 洩漏欄位（保留率 0.961300）。審查者照報告去查，會看到審查前的舊版。
2. **EZKL 綁定只解決一半，摘要對 EZKL 的主張超出證據。** 單輪證明閘的「合法 proof、替換向量」確實會被拒絕（已實測），但伺服器的 `verified` 讀自客戶端 pipeline 寫的 `summary.json`，vk、SRS、settings 也由各客戶端自行產生。摘要（tex 111、122 行）說「15 至 1,991 維均能拒絕偏移 1 單位的篡改」，但 999 與 1,991 維沒有篡改案例，42、385、650 維的拒絕來自 artifact 旗標，正是審查意見 1 指出的同一個問題。
3. **封面四個欄位仍空白，計畫年度與報告日期待確認。** 計畫編號、執行期間、系所、指導教授（tex 90–93 行）只能由作者填寫。另外國科會作業要點規定報告須經指導教授確認；若本計畫是 115 年度（2026-07-01 至 2027-02-28），封面的「115 年 10 月」早於執行期滿。

數字本身的品質很好：450 項數字自動核對有 448 項與原始檔一致，Titanic 與 Heart Disease 重跑逐位重現，隱私會計獨立重算落在報告值之下（報告值是保守上界）。需要修的是主張範圍與公開可見性，不是數據。

## 問題 1：交付前必須改（阻擋）與建議改（非阻擋）

### 阻擋

| # | 位置 | 問題 | 建議修正 |
|---|---|---|---|
| B1 | tex 90–93、98 | 封面計畫編號、執行期間、系所、指導教授空白；日期「115 年 10 月」需與計畫年度對照 | 作者提供後填入，不可代填。請確認計畫年度與繳交期限（作業要點：期滿後三個月內線上繳交，須經指導教授確認） |
| B2 | tex 100、658；git | `564c3f4`、`5e6885b` 未 push；遠端 `main` 為 `4623db8`（舊 Titanic、無 Heart Disease） | push 由作者決定。push 後二擇一：合併 PR #4 進 `main`（合併由作者決定），或把封面網址改成指向分支或 commit 的完整連結（例如 `.../tree/<commit>`）。新增的 `test_gate.py` 與 pattern 會計測試在 CI 從未跑過，push 後應確認 CI 通過 |
| B3 | tex 111、122（摘要） | 「EZKL 實際證明在 15 至 1,991 維完整更新向量上均能拒絕僅偏移 1 個量化單位的篡改」證據不支持。`production_scaling/results/actual_ezkl_proof_scaling.csv` 9 列全是誠實案例；`zk_cost_scaling_runs.csv` 0 筆篡改；`multiclass_vdp_zk/run_wine_vdp_zk_cost.py:279` 只有公開輸出 `checks`，第 337 行 `accepted` 由 artifact 旗標決定；`covertype_large_dataset_scaling/run_covertype_vdp_zk.py:44` 直接把篡改案例的旗標寫成 False | 改寫為：單輪 Adult 證明閘以公開 `q_noisy` 的實際證明拒絕篡改；15 至 1,991 維只量測誠實案例的證明成本。或者對高維線補跑公開 `q_noisy` 的篡改案例後保留原句 |
| B4 | tex 241、328；`proof_gated_round/run_actual_proof_gated_round.py:186` | 伺服器沒有自己呼叫 `ezkl.verify`，`verified` 取自客戶端寫的 `summary.json`；vk、SRS、settings 由各客戶端各自 `gen_srs`、`setup`，三個客戶端的 vk 互不相同。實測：用惡意電路（checks 恆為 0、q_noisy 為篡改向量）配它自己的 vk，驗證為 True，gate 接受 | 最低限度：在 §4.3 與 §5.2 寫明信任假設（伺服器固定 vk、settings 與可信 SRS；本實驗以單機模擬，`gen_srs` 為測試用）。較好：讓伺服器以固定 vk 對同一份 proof 物件呼叫 `ezkl.verify` 再解碼，並新增「換 vk 或電路」「proof 驗不過但旗標為 True」兩個拒絕測試，重跑後更新 `statements.json`（約半天到一天） |
| B5 | tex 263 | 「嚴格表述是：在 Poseidon 構造對唯一輸入為安全 PRF 的假設下，對多項式時間驗證者為 computational (ε, δ+Adv_PRF)-DP」把未完成的證明寫成已成立，與下一句矛盾；δ 項也不對，由 TV 距離或 PRF 優勢轉換時應為 δ+(1+e^ε)·η，e^28.84 約 3.35×10¹² | 改成條件句，例如「若完成 PRF hybrid 與 transcript 模擬，預期可得 computational DP，其 δ 項需加上 (1+e^ε) 倍的 PRF 優勢」。tex 608 行「Poseidon 版的 computational DP 依賴……」同樣改為條件式 |

B3 到 B5 都是改寫幾句話即可解除阻擋；B4 若選擇修程式則需要重跑 EZKL。

### 非阻擋（建議改）

| # | 位置 | 問題與建議 |
|---|---|---|
| N1 | tex 328 | 「單元測試另覆蓋長度不符與偽造旗標的情形」：`decide` 本來就不收旗標，`test_gate.py:107-113` 只是重述實作。建議刪去「偽造旗標」 |
| N2 | tex 162 | Nasr 等人的敘述正確，建議把「主要貢獻正是」改為「主要貢獻之一是」，括號改為「在審計者可觀察每步 DP-SGD 更新並插入梯度金絲雀的白箱設定下」 |
| N3 | tex 389 | 「最近一次（2026-10-05）全部通過」：`gh run list` 最近一次成功為 2026-10-18（PR 分支 `d970126`）；10-05 是 `main` 最後一次成功。`1.8452±0.0407` 是 95% CI 半寬（標準差 0.0569），應標明 |
| N4 | tex 573 | Digits proof bytes 寫 11,988，`zk_cost_scaling_summary.csv` 平均 11,990.667，應為 11,991 |
| N5 | tex 596 | 「17 個資料集、CoverType」把 CoverType 算兩次（17 = 12 二元 + 3 多類別 + Adult + CoverType） |
| N6 | 附錄 A | 漏列 `quantization_scale_sweep/`（tex 300 行的 8/12/16 數字來源）與 `fedavg_baseline/`、`dp_fedavg_baseline/`（S0/S1 數字來源） |
| N7 | §3.2 tex 164 | 「較少把噪聲生成、裁剪與多輪聯邦聚合綁在同一證明關係內。本研究補的正是這一段」：VeriDP（PoPETs 2026(3):48–64）已逐次迭代以 ZK 證明 DP-SGD 的梯度計算、裁剪與 Gaussian 噪聲生成，Confidential-DPproof（ICLR 2024）也相關。建議補引並把定位改為「秘密隨機性的 commit-before-challenge 情境綁定與證明閘聚合」 |
| N8 | ref.bib | `biswas2022verifiable` 已正式發表於 CCS 2023（pp.1919–1933，doi 10.1145/3576915.3616681）；`kwon2025verifying` v2 改題為 "Verifiable Exponential Mechanism for Median Estimation"；`wei2025verifiable` 補 article 14 與 doi 10.1007/s44443-025-00028-z；`ahmed2025zkai` 作者順序依 Crossref 為 Ahmed、Ahmad、Suneel、Bhatia、D、Singh，補 pp.1716–1722；`janosi1988heart` UCI 建議年份為 1989；`halo2repo` 作者寫成 Zcash Foundation 可能不對（推論：開發者應為 Electric Coin Company） |
| N9 | §5.8 tex 482 | Titanic 仍以 one-hot 保留 name（1,307 種值）、ticket（929）、cabin（186）、home.dest（369），input_dim 2,330。這不是結果洩漏，但屬近似 ID 記憶，cabin 與 home.dest 的缺值本身與存活相關。本審查在 scratchpad 的敏感度重跑（六欄全刪，input_dim 10）得 FL 0.751909、DP 0.740458、保留率 0.984771，結論不變。若要寫進報告，需由作者在 repo 內重跑並保留原始結果 |
| N10 | tex 258 | 「客戶端 $k$」與噪聲參數 $k=16$ 撞名 |
| N11 | tex 4 | 註解寫 `latexmk -xelatex`，但本機 latexmk 會被 MiKTeX 安裝對話框卡住；實際做法是 `xelatex --disable-installer` 三次加 `bibtex` |
| N12 | 輔助文件 | 仍有過強或過時措辭（不影響 PDF，但審查者可能點進 repo）：`docs/publication/strengthening-report.md:16, 85`（「已完成」與無條件 computational-DP 敘述）；`experiments/discrete_noise_accounting/results/summary.md:13-14`（由 `centered_binomial_accountant.py:248-250` 產生）；`experiments/discrete_noise_accounting/formal_dp_theorem.md:66-73` 稱 theorem，與同檔 86–95 行矛盾；`docs/publication/manuscript-source.txt:205, 338`、`docs/nstc/report-draft.md:386, 388`、`docs/nstc/experiment-summary.md:53` 仍是 11 個資料集與舊 Titanic 數字；`assets/readme/scaling-and-robustness.svg:7` 的「under 2 s up to 1,991 dims」指 EZKL，容易被誤讀成 Halo2 |
| N13 | 公開設定 | 作業要點規定成果報告預設立即公開；若打算投稿且擔心先行公開，可申請延後公開（最長兩年，需另交精簡報告）。workshop（non-archival）與 arXiv 一般不受影響，這是作者的選擇 |

## 問題 2：上一輪七項意見與三項小修是否真的解決

| 意見 | 判定 | 證據 |
|---|---|---|
| 1 EZKL 綁定 | **部分解決** | 已解決的部分：`q_noisy` 改為公開輸出；把 `proof.json` instances 中 `q_noisy` 任一正或負座標 +1 後，`ezkl.verify`（10.2.7）回報 constraint system not satisfied；只改 `pretty_public_inputs` 不影響驗證，gate 也不讀它；未約化別名 x+p 會被拒；proof 不動、提交向量偏移 1 被 gate 拒絕；三個客戶端的解碼值與 `witness.json` 逐元素相同，clip 98,890,825／99,337,085／100,010,941、殘差 0／1／0，scale 26／13 解碼正確。`proof_gated_round` 單元測試 13/13 通過。未解決的部分：B3、B4 |
| 2 DP 措辭 | **大致解決，差一句** | 摘要（111、122）、§5.5（442）、§6.1（605）、附錄 A（673）均已改為理想機制會計值。殘留 tex 263、608（B5），以及 N12 的輔助文件 |
| 3 Titanic | **已解決（本機）** | `run_multi_dataset_repeats.py:40` 設 `drop_columns`，第 75–80 行在切分與前處理前刪欄，前處理只在 train fit。scratchpad 重跑逐位重現 0.755725／0.739186／0.978114，表 9 的 12 列與 summary CSV 0 筆不符，9/12 正確。但結果只在未 push 的 `564c3f4`（B2） |
| 4 Heart Disease | **內容已解決，可見性未解決** | 程式與結果在 `bf2dd27`，已在遠端 PR 分支；重跑逐位重現 0.743169／0.617486／0.830882，各 seed DP 0.655738／0.754098／0.442623。附錄 A 對 commit 的描述正確。遠端 `main` 沒有（B2） |
| 5 Nasr 引用 | **已解決** | tex 138、162 行方向正確（Nasr 等人把緊審計降到兩次訓練）；N2 為措辭精修 |
| 6 高維 ε | **已解決** | 窮舉 d=8 所有合法向量對，(a,b) 集合恰為 a≤4、2a+b≤8。以 60 位精度確認單一位移 2 的 hockey-stick 在全部斷點都大於等於兩個位移 1 的組合，所以 (4,0) 對所有 ε dominate，逐輪取最壞再做適應性組合合法。各 pattern 10 輪 ε：(4,0) 28.79、(3,2) 26.27、(2,4) 23.65、(1,6) 20.89、(0,8) 17.96。boundary.json 的 5.9e-5、3.1e-4 確為「每座標皆位移 2」的下限，tex 424 敘述正確。repo 的程式只在 δ=1e-5 一點比較 pattern（`fixed_norm_pattern_accounting.py:17, 172`），論證應補進文件，結論不受影響 |
| 7 證明時間 | **已解決** | 由 5 個 `run.json` 重算 n=150、平均 1.95195、中位數 1.6468、最大 3.99358（seed 82）、60 份超過 2 秒，與 tex 405、627、674 及 README、claim-evidence-map C12 一致；repo 已無「所有證明 <2 秒」的錯誤主張 |
| 小修 [11] | **已解決** | Bontekoe、Asghar、Turkmen，PoPETs 2025(2):543–563，doi 10.56553/popets-2025-0076 |
| 小修 封面 | **未解決** | B1，需作者提供 |
| 小修 U+2010 | **已解決** | PDF 內 U+2010 剩 4 處，都在封面與參考文獻的 URL 排版字元，連結目標正確；附錄 B 指令全為 ASCII |

## 問題 3：數字、主張或引用與原始檔不符之處

數字核對以腳本執行（每筆先確認數字出現在 tex 標示行，再由原始 CSV/JSON 重算；另放三個故意出錯的對照組確認腳本會抓到錯）。450 項中 448 項一致、2 項不符、0 項找不到。兩項不符是 N3 的 CI 日期與 N4 的 Digits proof bytes。過去被標為「無法從原始檔確認」的項目都找到來源並吻合：量化尺度 8/12/16 在 `quantization_scale_sweep/results/scale_sweep_results.csv`；5/9、0/9、9/9、18/18、4200/73300 ppm 在三個約束實驗的 results CSV；`paired_effects.csv` 33 列、Holm 後 0 組；Halo2 原始碼有 8 個 `#[test]`。表 multiround 的 95% CI（t(4)、以軌跡為單位）全部吻合。PDF 由 tex 編譯而來，174 個三位以上小數全部出現在 PDF。

隱私會計獨立重算（自寫 PLD，以上下取整夾出區間，並與小 n 精確乘積分布比對）：

| 情境 | 獨立重算 ε 區間 | 報告值 |
|---|---|---|
| k=16，40 次 | [28.7879, 28.7916] | 28.840669 |
| k=16，80 次 | [46.7461, 46.7605] | 46.855616 |
| k=32，40 次 | [17.9344, 17.9382] | 17.979538 |
| k=64，40 次 | [11.4970, 11.5008] | 11.541361 |
| k=32，200 次 | [54.4520, 54.5251] | 54.709923 |

報告值都略高於重算上界（差 0.04 到 0.18），來自 grid 0.002 向上取整，方向保守。δ 下限 3.07×10⁻⁷ 以有理數精確重算一致。域位元偏差 5.9×10⁻⁶⁶ 是正確但寬鬆的上界。

主張與證據不符的地方就是 B3、B4、B5、N1、N7。引用方面沒有找到捏造或無法查證的文獻；需更新的書目列在 N8。

## 問題 4：投稿學術論文還缺什麼（依優先順序）

| 優先 | 項目 | 為什麼 | 估計工作量 |
|---|---|---|---|
| 1 | 伺服器端驗證與信任設定 | 審查者會直接問 B4；伺服器必須以固定 vk、settings、可信 SRS 自行驗證，並有對應的拒絕測試 | 0.5–1 天 |
| 2 | 定位與相關工作 | VeriDP（PoPETs 2026）、Confidential-DPproof（ICLR 2024）、zkDL、RoFL、Sabater 等人的可驗證聯邦 DP 平均、VerDP（EuroSys 2015）都需要比較表；目前「本研究補的正是這一段」站不住 | 1–2 週 |
| 3 | 形式化安全分析 | 定義證明閘的 soundness 與 binding、transcript 的 computational DP（PRF hybrid、commitment hiding、ZK simulation、δ 項加上 (1+e^ε)·Adv）、dominating-pair 適應性組合、selective abort 與重試 | 3–6 週 |
| 4 | 有意義的隱私預算與高維隱藏隨機性 | 目前只有 d=4、ε≈28.84；高維 EZKL 線是公開種子（ε=∞）。可考慮較大 k、Skellam 或離散 Gaussian、搭配 secure aggregation 的分散式噪聲以降低每客戶端噪聲 | 1–3 個月 |
| 5 | 真實資料與混合接受／拒絕的 live 多輪實驗 | 四維電路目前只用合成資料；威脅矩陣 1,440 次是政策模擬 | 2–4 週 |
| 6 | 英文論文撰寫 | 12–13 頁會議格式：威脅模型、系統、安全性、評估、限制 | 3–4 週 |

只投 non-archival workshop 時，做完 1、B3–B5 的措辭修正、2 的簡短相關工作即可。正式會議至少要 1 到 3；PoPETs 等級需要 1 到 5 全部。

## 問題 5：適合的 venue（查證日 2026-10-20）

整體判斷：現在的成果適合 workshop 與 arXiv，還不到頂會門檻（computational-DP 證明未完成、ε 大、沒有與既有系統比較）。2026 年 11 到 12 月截稿的頂會（IEEE S&P 2027 cycle 2、EuroS&P 2027、AsiaCCS 2027 R2）不建議硬投。AsiaCCS 2027 CFP 另明寫不鼓勵主要聚焦 ML 的投稿。

| 類型 | 選項 | 截止日 | 適合度與前提 |
|---|---|---|---|
| Workshop | [AAAI-27 Deployable AI (DAI)](https://dai-workshop.github.io/) | 2026-11-20 AoE（已親自核對）；通知 12-02；會議 2027-02-22～23 Montréal | 4 或 7 頁，雙盲，non-archival，主題含 Privacy-Preserving AI。用現有成果加上 B3–B5 修正與匿名化 repo 即可 |
| Workshop | [ACNS 2027 workshops](https://acns2027.isg.rhul.ac.uk/calls/workshops) | workshop 提案截止 2027-02-19，論文截止依各 workshop | LNCS post-proceedings（archival），需親自出席英國。需補安全性定義與證明草稿 |
| Workshop | TPDP 2027、ZKProof 9、HotPETs 2027 | 推估 2027 年 2–5 月（只查到 2026 屆：[TPDP 2026](https://differentialprivacy.org/tpdp2026/) 2026-02-18、[ZKProof 8](https://zkproof.org/call-for-papers-8th-zkproof-workshop/)、[HotPETs 2026](https://petsymposium.org/2026/hotpets.php)） | 都是 non-archival。ZKProof 對 Halo2 電路工程最對口；TPDP 會直接質疑 ε 太大；HotPETs 適合談負面結果 |
| Workshop | [ICLR 2027 workshops](https://iclr.cc/Conferences/2027/CallForWorkshops)、[IEEE SPW 2027](https://sp2027.ieee-security.org/cfworkshops.html) | 入選 workshop 名單分別於 2026-11-29、2026-11-10 公布 | 要等名單出來再看有沒有 privacy 或 trustworthy ML 主題 |
| 會議 | [PoPETs 2027](https://petsymposium.org/cfp27.php) | Issue 3：2026-11-30；Issue 4：2027-02-28（已親自核對，皆為 firm） | 最對題。被拒須隔一期才能重投，所以 11-30 不建議投。實際目標是 PoPETs 2028 Issue 1（推估 2027-05-31），前提是完成第 4 節 1–5 項 |
| 會議 | [ACNS 2027](https://acns2027.isg.rhul.ac.uk/) | Cycle 2：2027-01-21 | 有最佳學生論文獎。需補 game-based 定義與 soundness／binding 證明，時間偏緊 |
| 會議 | [USENIX Security '27](https://www.usenix.org/conference/usenixsecurity27) | Cycle 2：註冊 2027-01-19、全文 01-26 | 頂會，需先補完所有弱點，不建議 |
| 會議 | ESORICS 2027、CCS 2027、ACSAC 2027、CISC 2027（中華民國資訊安全學術研討會） | 查不到 2027 CFP；依往年推估 ESORICS 1 月與 4 月、ACSAC 約 5 月下旬、CISC 約夏季 | CISC 適合作為國內發表與學生曝光 |
| 期刊 | [IEEE TDSC](https://computer.org/csdl/journals/tq/write-for-us/15068)、IEEE TIFS、[Journal of Privacy and Confidentiality](https://journalprivacyconfidentiality.org/index.php/jpc/about) | 隨時投稿 | 形式化補完後的完整版；JPC 適合 DP 會計加系統的長文 |
| 期刊 | [IEEE Access](https://ieeeaccess.ieee.org/) | 隨時投稿，官網寫約 4–6 週 | 快但評價普通，收 APC，當作保底 |
| 預印本 | arXiv cs.CR（cross-list cs.LG） | 隨時 | [2026-01-21 起](https://blog.arxiv.org/2026/01/21/attention-authors-updated-endorsement-policy/) 自動 endorsement 需機構信箱加上同 domain 已有論文；大學部首次投稿通常需請指導教授做個人 endorsement（[作法](https://info.arxiv.org/help/endorsement.html)）。若同時投雙盲 workshop，留意 arXiv 時間與匿名規定 |
| 學生 | 國科會大專生研究創作獎 | 依計畫年度（成果報告即評選依據，期滿後三個月內繳交） | 每年至多 200 名。依[台大轉載公告](https://ann.ch.ntu.edu.tw/post/20484/)，115 年度執行期為 2026-07-01 至 2027-02-28；請向中央大學研發處確認本計畫年度與期限 |

建議路線（工作量為估計）：

1. 2026-11 上旬：完成本報告的 B1–B5 並交付；同時修 B4 的程式（約 1 天）。
2. 2026-11-20：投 AAAI-27 DAI workshop 長文 7 頁（約 1 週：英文改寫、威脅模型、限縮主張、匿名化 repo）。
3. 2026-11 下旬到 12 月：arXiv cs.CR（約 3 天，加上找 endorser）。
4. 2027-01 到 02：依形式化進度，衝 ACNS 2027 cycle 2（01-21），來不及就投 ACNS workshop 或 PoPETs 2027 Issue 4（02-28，stretch）。
5. 2027-02 到 05：TPDP、ZKProof、HotPETs 摘要（每份約 3–5 天，日期待 CFP 公布）。
6. 2027-05-31（推估）：PoPETs 2028 Issue 1 完整論文（3–4 個月：computational-DP 證明、高維隱藏隨機性、與 VeriDP 等系統比較）。

## 驗證紀錄與未驗證項目

本 session 與其 agent 實際執行的檢查：

- `proof_gated_round` 單元測試 13/13、`discrete_noise_accounting` 12/12、`actual_multiround_halo2` 3/3，以 `C:/Users/USER/anaconda3/python.exe -m unittest` 執行。
- EZKL 對抗實驗以 `conda run -n zkML python`（ezkl 10.2.7）對既有 proof 執行，腳本與結果在 scratchpad `ezkl/attack.py`、`attack_results.json`。未重跑 `run_actual_proof_gated_round.py`，因為它會寫入 repo 內目錄。
- Titanic 與 Heart Disease 以 `run_multi_dataset_repeats.py --output-dir <scratchpad>` 重跑，與 repo CSV diff 相同。只在同一台機器、同一份 OpenML 快取下驗證。
- 隱私會計獨立重算腳本在 scratchpad `accounting/independent_recompute.py`。
- 數字核對腳本在 scratchpad `numbers/check_numbers.py`，核對表為同目錄 `numbers_check.csv`。
- Halo2 `cargo test --release`（`CARGO_TARGET_DIR` 指向 scratchpad）：8 passed，0 failed，與 tex 389 行「8 個測試」及其名稱一致。

未驗證：

- 沒有重新產生任何 Halo2 證明或 150 份多輪證明，只核對既有原始檔。
- 沒有核對 Halo2 電路是否確實每座標每輪各用一個域元素（PLD 40 次組合的前提）。
- 沒有在其他機器或其他 sklearn、torch、EZKL 版本上驗證重現性。
- 國科會大專生成果報告的官方撰寫格式（頁數、必備章節）沒有找到官方原文；本審查只依作業要點條文確認繳交期限、指導教授確認與公開規定。
- 各 2027 workshop 的實際截止日、PoPETs 與 ACNS 頁數規定、期刊審稿週期未查到官方資料。
