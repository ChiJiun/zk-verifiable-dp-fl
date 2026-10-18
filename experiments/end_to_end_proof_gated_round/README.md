# end-to-end proof-gated round - End-to-End S2 Round

end-to-end proof-gated round 的目標是把 proof-gated aggregation 實際套回 global model，形成一輪更完整的 S2 round outcome。

## 執行方式

```bash
python experiments/end_to_end_proof_gated_round/run_end_to_end_s2_round.py
```

## 輸出

- `results/accepted_average_q_noisy.json`
- `results/ungated_average_q_noisy.json`
- `results/summary.md`

## 重要說明

- 這一步讀取 `proof_gated_round/results/statements.json`：`proof-gated` 版本聚合的是各 client **證明中公開的** `q_noisy`（由 proof instances 解碼），不再從 `constraint_artifacts` 讀取向量；artifact 只用來取得張量形狀
- `proof-gated` 版本只聚合通過 proof、約束與向量綁定檢查的 client
- 需要 `experiments/adult_income_model/data/processed/`（由 `adult_income_model/data_preprocessing.py` 產生，不版控）
- `ungated` 版本會把所有 selected updates 一起聚合，作為對照
