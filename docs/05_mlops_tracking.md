# 05_mlops_tracking.md

## Quick Reference
- **Platform**: DagsHub (Managed MLflow).
- **Goal**: Experiment tracking, transparency, and reproducibility.

## Metrics Logged During Pipeline
When `notebooks/colab_pipeline.ipynb` runs, it automatically logs the following to DagsHub MLflow:
- `total_movies_processed`: Number of movies evaluated in the pipeline.
- `movies_filtered_by_rating`: How many low-quality movies were dropped at the Quality Gate.
- `Recall@10` & `NDCG@10`: Offline ranking metrics to evaluate retrieval performance.
- `vector_db_size`: Monitored to ensure the artifact remains lightweight and portable.

## Why MLflow?
MLflow separates the code from the experiment results. By logging metrics alongside the hyperparameters (e.g., the `all-MiniLM-L6-v2` model name, Reranker weights), any engineer can trace back why a specific `lancedb_movies.zip` artifact performs the way it does without having to re-run the heavy Colab notebook.