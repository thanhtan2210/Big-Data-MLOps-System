# 05_mlops_tracking.md

## Quick Reference
- **Platform**: DagsHub (Managed MLflow).
- **Goal**: Experiment tracking, transparency, and reproducibility.

## Metrics Logged During Pipeline
When `notebooks/colab_pipeline.ipynb` runs, it automatically logs the following to DagsHub MLflow:
- `Recall_k10`: Offline recall score at top-10 retrieval (Baseline: **88.56%**).
- `NDCG_k10`: Normalized Discounted Cumulative Gain at top-10 (Baseline: **0.81**).
- `total_movies_processed`: Number of movies evaluated in the pipeline (13,164 movies).
- `movies_filtered_by_rating`: How many low-quality movies were dropped at the Quality Gate.
- `vector_db_size`: Monitored to ensure the artifact remains lightweight and portable.

## Why MLflow?
MLflow separates the code from the experiment results. By logging metrics alongside the hyperparameters (e.g., the `all-MiniLM-L6-v2` model name, Reranker weights), any engineer can trace back why a specific `lancedb_movies.zip` artifact performs the way it does without having to re-run the heavy Colab notebook.