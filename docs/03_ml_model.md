# 03_ml_model.md

## Quick Reference
- **Embedding Model**: `SentenceTransformer` (`all-MiniLM-L6-v2`, 384D).
- **Personalization**: Pseudo-Tower (Weighted Average).
- **Reranker Layer**: 60% Similarity + 30% Popularity + 10% Quality.

## Pseudo-Tower Personalization
Instead of running a heavy Two-Tower Neural Network that requires 24/7 inference servers, we simulate the User Tower mathematically. 
Given a list of movies a user likes, we extract their 384D vectors from LanceDB and compute the **Weighted Average Vector** (using the user's ratings as weights). This resulting vector accurately represents the user's position in the latent space, perfectly serving as the query vector for KNN searches.

## Reranker Formulation
Cosine similarity algorithms often return niche, highly identical items. To balance discovery and quality, candidate results are rescored using a hybrid equation:
`Final_Score = 0.6 * Similarity + 0.3 * Popularity + 0.1 * Quality`
- **Similarity**: Raw cosine distance from LanceDB.
- **Popularity**: Normalized `rating_count`.
- **Quality**: Normalized `avg_rating`.

## Evaluation Metrics (Logged to MLflow)
- **Recall@10**: Percentage of highly-rated holdout movies successfully retrieved.
- **NDCG@10**: Quality of the ranking order (discounting relevant items pushed to the bottom of the list).