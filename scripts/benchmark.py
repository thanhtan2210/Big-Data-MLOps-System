import os
import time
import numpy as np
import pandas as pd
import lancedb
from src.serving.semantic_search import Reranker

def run_benchmark():
    db_uri = "notebooks/tmp_lancedb"
    print(f"Connecting to existing database at: {db_uri}")
    
    if not os.path.exists(db_uri):
        print(f"Error: Database directory {db_uri} not found. Please run notebooks or streamlit app first.")
        return
        
    db = lancedb.connect(db_uri)
    tables = db.table_names()
    print(f"Found tables: {tables}")
    
    # Prefer 'movies_real' if present, otherwise fallback to 'movies'
    table_name = "movies_real" if "movies_real" in tables else "movies"
    if table_name not in tables:
        print(f"Error: Table 'movies' or 'movies_real' not found in {db_uri}.")
        return
        
    print(f"Using table '{table_name}' for benchmark...")
    table = db.open_table(table_name)
    num_rows = table.count_rows()
    print(f"Table contains {num_rows} records.")
    
    # Dynamically check vector dimension
    first_batch = table.head(1)
    vector_data = first_batch['vector'].to_pylist()
    if not vector_data or len(vector_data[0]) == 0:
        print("Error: Could not retrieve vector dimension from table.")
        return
    dim = len(vector_data[0])
    print(f"Detected vector dimension: {dim}")
    
    # Warm-up queries
    print("Warming up database connection...")
    for _ in range(10):
        q = np.random.rand(dim).tolist()
        table.search(q).metric("cosine").limit(20).to_pandas()
        
    num_queries = 100
    search_latencies = []
    rerank_latencies = []
    total_latencies = []
    
    print(f"Running {num_queries} queries for benchmark...")
    for _ in range(num_queries):
        # Generate random query vector of matching dimension (unit vector)
        vec = np.random.rand(dim).astype(np.float32)
        query_vector = (vec / np.linalg.norm(vec)).tolist()
        
        # Measure LanceDB search latency
        t0 = time.perf_counter()
        results_df = table.search(query_vector).metric("cosine").limit(20).to_pandas()
        t1 = time.perf_counter()
        
        # Measure Rerank latency
        candidates = []
        for _, row in results_df.iterrows():
            candidates.append({
                "movie_id": int(row.get("movieId", row.get("movie_id", 0))),
                "title": str(row.get("title", "Unknown")),
                "genres": str(row.get("genres", "")),
                "overview": str(row.get("overview", "")),
                "poster_path": str(row.get("poster_path", "")),
                "avg_rating": float(row.get("avg_rating", 0.0)),
                "rating_count": int(row.get("rating_count", 0)),
                "similarity_score": round(1.0 - row["_distance"], 4) if "_distance" in row else 0.5
            })
            
        t2 = time.perf_counter()
        Reranker.rerank(candidates)
        t3 = time.perf_counter()
        
        search_latencies.append((t1 - t0) * 1000)
        rerank_latencies.append((t3 - t2) * 1000)
        total_latencies.append((t3 - t0) * 1000)
        
    # Calculate statistics
    def get_stats(latencies):
        return {
            "mean": np.mean(latencies),
            "p50": np.percentile(latencies, 50),
            "p95": np.percentile(latencies, 95),
            "p99": np.percentile(latencies, 99)
        }
        
    search_stats = get_stats(search_latencies)
    rerank_stats = get_stats(rerank_latencies)
    total_stats = get_stats(total_latencies)
    
    print("\n" + "="*50)
    print(f"LANCEDB BENCHMARK RESULTS ({num_rows} records, {dim}D)")
    print("="*50)
    print(f"Operation          | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms)")
    print("-"*50)
    print(f"LanceDB Raw Search | {search_stats['mean']:9.2f} | {search_stats['p50']:8.2f} | {search_stats['p95']:8.2f} | {search_stats['p99']:8.2f}")
    print(f"Reranking Layer    | {rerank_stats['mean']:9.2f} | {rerank_stats['p50']:8.2f} | {rerank_stats['p95']:8.2f} | {rerank_stats['p99']:8.2f}")
    print(f"End-to-End Search  | {total_stats['mean']:9.2f} | {total_stats['p50']:8.2f} | {total_stats['p95']:8.2f} | {total_stats['p99']:8.2f}")
    print("="*50 + "\n")
    
    # Save results to docs/benchmark_results.md
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    benchmark_file = os.path.join(docs_dir, "benchmark_results.md")
    
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    markdown_content = f"""# LanceDB Vector Search Benchmarks

- **Run Timestamp:** {timestamp}
- **Dataset Size:** {num_rows:,} records
- **Vector Dimension:** {dim}D
- **Number of Trials:** {num_queries} queries

## Performance Metrics

| Operation | Mean Latency (ms) | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **LanceDB Raw Search** | {search_stats['mean']:.2f} | {search_stats['p50']:.2f} | {search_stats['p95']:.2f} | {search_stats['p99']:.2f} |
| **Reranking Layer** | {rerank_stats['mean']:.2f} | {rerank_stats['p50']:.2f} | {rerank_stats['p95']:.2f} | {rerank_stats['p99']:.2f} |
| **End-to-End Vector Retrieve** | {total_stats['mean']:.2f} | {total_stats['p50']:.2f} | {total_stats['p95']:.2f} | {total_stats['p99']:.2f} |

---
*Note: Benchmarks were run using the pre-existing database table '{table_name}' in '{db_uri}'.*
"""
    with open(benchmark_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"Results successfully saved to {benchmark_file}")

if __name__ == "__main__":
    run_benchmark()
