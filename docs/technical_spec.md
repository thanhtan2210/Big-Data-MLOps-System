# Technical Specification

The system is architected based on **Serverless Cloud-native MLOps** principles, entirely eliminating the dependency on physical servers or 24/7 VPS instances.

## 1. Storage Layer (Cloudflare R2)
- Serves as the central Data Lake.
- Stores raw datasets: `movies.csv`, `ratings.csv`, `tags.csv`, `genome`.
- Stores Vector Artifacts: The processed `lancedb_movies.zip` ready for distribution with zero egress fees.

## 2. In-memory Vector Database (LanceDB)
- Deployed as an embedded library within the Hugging Face Python process.
- **Schema**: Strictly constrained using PyArrow `FixedSizeList(384)` for the vector column.
- **Queries**: Applies a **Flat Search** mechanism combined with **Pandas Metadata Filtering** for extremely safe ID lookups and decade filtering.
- **Personalization**: Utilizes **Pseudo-Tower Personalization** (Weighted Average Vector from user history).

## 3. AI Agent & LLM
- **Model**: `Llama-3.3-70b-versatile` via Groq API (utilizing LPU hardware for ultra-low latency).
- **Pure RAG Architecture**: Queries LanceDB first, concatenates movie info into a Context string, and injects it into the LLM's System Prompt to completely eliminate Hallucinations.
- **Function Calling**: The LLM is equipped with 5 Tools (Semantic Search, Find Similar, Compare, Filter by Decade, Trending Movies).
- **Entity Memory**: Stores the user's favorite genres during the conversation session (Session State).
- **Smart Fallback**: Redirects to offline vector retrieval when the API exhausts its Quota.

## 4. Frontend Interface (Streamlit)
- **Environment**: Hugging Face Spaces (Scale-to-zero when there's no traffic).
- Features 5 Analytics Dashboards using Plotly Express, streaming a capped maximum of 500k data rows.
- Integrates a real-time **Lookup Dictionary**, allowing users to select movies by **Title** rather than memorizing dry ID numbers.