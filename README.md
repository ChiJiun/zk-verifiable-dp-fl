# zk-verifiable-dp-fl

可驗證差分隱私聯邦學習（VDP-FL）研究原型。客戶端以零知識證明說明自己的更新確實經過裁剪與加噪；伺服器驗證證明、情境與重播狀態後，只聚合通過的更新。

[![Reproducibility matrix](https://github.com/ChiJiun/zk-verifiable-dp-fl/actions/workflows/reproducibility-matrix.yml/badge.svg)](https://github.com/ChiJiun/zk-verifiable-dp-fl/actions/workflows/reproducibility-matrix.yml)

完整說明見國科會結案報告：[`docs/nstc/final-report/final-report.pdf`](docs/nstc/final-report/final-report.pdf)。

## 兩條證明線

| | EZKL 約束線 | Halo2 秘密隨機性線 |
|---|---|---|
| 證明內容 | 裁剪上界與加性關係 `q_noisy = q_clipped + q_noise` | 秘密承諾、commit-before-challenge 情境、Poseidon PRG、centered-binomial 取樣（k=16）、裁剪與加性關係 |
| 規模 | 15 至 1,991 維完整更新 | d=4，合成資料 |
| 噪聲 | 公開種子；`q_noise` 是不受約束的私有 witness | 由設定期秘密與本輪情境在電路內產生 |
| 能做到 | 綁定被聚合的向量、拒絕 witness 自身不一致的客戶端 | 限制更新幅度；理想機制 ε ≈ 28.84（δ=1e-5） |
| 做不到 | 限制更新幅度；驗證者視角 ε = ∞ | 高維效用；完整協定的 computational-DP 證明 |

## 主要結果

| 結果 | 證據類型 | 位置 |
|---|---|---|
| 150/150 份逐更新 Halo2 證明通過、磁碟重驗 150/150、7 類負面探測 1,050/1,050 被拒（3 客戶端 × 10 輪 × 5 seeds） | 實際證明 | `experiments/actual_multiround_halo2/` |
| 固定 d=4、k=16、10 輪的理想離散機制 ε ≤ 28.84 | 隱私會計 | `experiments/discrete_noise_accounting/` |
| EZKL 證明閘：替換提交向量、自選電路、驗證失敗旗標、小數殘差都被拒；把篡改移進私有噪聲的更新（每座標 ±10⁶）會被接受，是已知邊界 | 實際證明 | `experiments/proof_gated_round/` |
| 重播與零噪聲可通過只驗約束的閘；合法範圍內的符號反轉投毒在所有政策下都通過 | 政策模擬 | `experiments/multiround_threat_matrix/`、`experiments/robust_aggregation/` |
| 12 個二元資料集中 9 個在預設 DP 參數下保留 90% 以上 FL 準確率 | 效用實驗 | `experiments/binary_dataset_repeatability/` |

每項主張對應的腳本與結果檔，見[主張—證據對照](docs/research/claim-evidence-map.md)與報告附錄 A。

## 目錄

- `experiments/`：35 個研究單元，閱讀順序見[實驗索引](experiments/README.md)。
- `docs/nstc/final-report/`：結案報告的 LaTeX 原始檔與 PDF。
- `docs/research/`：威脅模型與主張—證據對照。
- `scripts/check_repository.py`：CI 使用的 repository 檢查。

## 重現

需求：Python 3.12、Rust stable（CI 不驗證 Python 3.13）。

### 核心測試（不需要 PyTorch 或 EZKL）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-core.txt

python scripts/check_repository.py
python -m unittest discover -s experiments/discrete_noise_accounting -p "test*.py" -v
cargo test --release --manifest-path experiments/halo2_verifiable_randomness/Cargo.toml
python -m unittest discover -s experiments/actual_multiround_halo2 -p "test*.py" -v
python -m unittest discover -s experiments/proof_gated_round -p "test*.py" -v
```

`proof_gated_round` 的 `ServerVerificationTests` 需要可執行 EZKL 的直譯器與本機產生的伺服器金鑰，沒有時會 skip。

### 完整 ML／EZKL 實驗

```powershell
python -m pip install -r requirements.txt
```

再依各實驗目錄的 README 執行。例如 EZKL 證明閘單輪：

```powershell
python experiments/proof_gated_round/run_actual_proof_gated_round.py --python <已安裝 torch 與 ezkl 的直譯器>
```

UCI Adult 原始資料、衍生的 NumPy arrays、`*.key` 與 `*.srs` 不納入版控，相關 pipeline 會重新下載或產生。

### Docker

容器只包含 privacy accountant 與 Halo2 電路，不包含 PyTorch／EZKL：

```powershell
docker build -t zk-verifiable-dp-fl-core .
docker run --rm zk-verifiable-dp-fl-core
```

### 編譯結案報告

```powershell
cd docs/nstc/final-report
xelatex --disable-installer -interaction=nonstopmode final-report.tex
bibtex final-report
xelatex --disable-installer -interaction=nonstopmode final-report.tex
xelatex --disable-installer -interaction=nonstopmode final-report.tex
```

中文使用標楷體（DFKai-SB）；沒有這個字型的環境會改用 Noto Serif TC。

## 授權

尚未選定開源授權；加入 `LICENSE` 前，請勿假設程式或資料可再散布。
