# LanceDB Vector Search Benchmarks

- **Run Timestamp:** 2026-07-10 14:53:05
- **Dataset Size:** 2,000 records
- **Vector Dimension:** 32D
- **Number of Trials:** 100 queries

## Performance Metrics

| Operation | Mean Latency (ms) | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **LanceDB Raw Search** | 4.79 | 4.55 | 6.71 | 7.39 |
| **Reranking Layer** | 0.02 | 0.01 | 0.03 | 0.04 |
| **End-to-End Vector Retrieve** | 6.87 | 6.28 | 10.46 | 11.26 |

---
*Note: Benchmarks were run using the pre-existing database table 'movies_real' in 'notebooks/tmp_lancedb'.*
