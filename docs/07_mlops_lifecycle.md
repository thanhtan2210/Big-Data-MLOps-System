# 07_mlops_lifecycle.md

## Concept: Serverless & Data-Centric MLOps
Unlike monolithic MLOps which focuses on continuous model training on dedicated clusters, this system implements a **Serverless, Data-Centric MLOps Lifecycle**. It prioritizes artifact portability, automated data quality gates, and zero-cost infrastructure maintenance.

## The 5 Pillars of the Lifecycle

### 1. Automated Data Pipeline (Data Engineering)
- **Environment**: Google Colab.
- **Workflow**: Automated streaming from Cloudflare R2 $\rightarrow$ PySpark Quality Filtering ($>50$ ratings) $\rightarrow$ Text Enhancement (Virtual Tokens) $\rightarrow$ Vectorization.
- **Outcome**: Ensures a consistent and reproducible feature extraction process from raw data to vector space.

### 2. Experiment & Metadata Tracking
- **Platform**: DagsHub (Managed MLflow).
- **Logged Metrics**: `total_movies_processed`, `movies_filtered_by_rating`, `embedding_model_name`, `vector_db_index_type`.
- **Significance**: Provides a transparent audit trail for every version of the movie database artifact generated.

### 3. Artifact Management (Model/Feature Registry)
- **Platform**: Cloudflare R2.
- **Process**: The generated LanceDB folder is compressed into `lancedb_movies.zip` and pushed to R2 with a global endpoint.
- **Role**: Serves as a stateless Model Registry, decoupling the Heavy Processing (Colab) from the Lightweight Serving (Hugging Face).

### 4. Serverless Continuous Deployment (CD)
- **Environment**: Hugging Face Spaces (Scale-to-zero).
- **Trigger**: User visit (Cold Start).
- **Logic**: Python `boto3` fetches the latest artifact $\rightarrow$ Unpacks into local ephemeral disk $\rightarrow$ In-memory mount.
- **Advantage**: Zero operational expenses (OpEx) during idle time while maintaining instant availability upon request.

### 5. Operational Monitoring & Smart Fallback
- **Environment**: Streamlit Health Monitor.
- **Monitoring**: Tracking Database Latency, Artifact Integrity, and API Quotas.
- **Resilience**: 
    - **Cold Start Fallback**: Popularity-based ranking for new users.
    - **API Fallback**: Local vector search if LLM provider (Groq) is rate-limited.
