# 04_deployment.md

## Quick Reference
- **Platform**: Hugging Face Spaces (Serverless).
- **Framework**: Streamlit.
- **Data Source**: Cloudflare R2.

## Deployment Lifecycle
1. **Cold Start**: The Space wakes up upon user visit. Streamlit triggers `boto3` to download `lancedb_movies.zip` from R2.
2. **Decompression**: The ZIP file is extracted to the local ephemeral disk.
3. **Database Init**: LanceDB connects to the local directory in-memory.
4. **App Ready**: Users can seamlessly interact with the Analytics Dashboards and the AI Concierge.

## Optimization & Stability
- **Dependency Pinning**: We strictly pin `httpx==0.27.2` to prevent Groq SDK networking conflicts, and `lancedb>=0.26.0` to ensure metadata compatibility (e.g., the `num_bits` parameter in the Colab indexing schema).
- **Pandas Metadata Filtering**: The DataFusion SQL parser inside LanceDB often struggles with identifier normalization (e.g., casing issues like `movieId` vs `movieid`). We completely bypass this by extracting the small database (13k rows) to a Pandas DataFrame in RAM and utilizing pure boolean indexing for exact metadata lookups, achieving 100% stability with a search latency of ~4.79ms (p50: 4.55ms, p95: 6.71ms) — see [benchmark_results.md](file:///d:/Bon%20Bon/SourceCode/git/Big-Data-MLOps-System/docs/benchmark_results.md).