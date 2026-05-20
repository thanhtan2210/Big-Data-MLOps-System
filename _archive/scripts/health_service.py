from fastapi import FastAPI, BackgroundTasks
import lancedb
import boto3
import os
import datetime
from typing import Dict, Any

app = FastAPI(title="Health Data System API", version="1.0")

# Initialize connections
LANCEDB_PATH = "notebooks/tmp_lancedb"
DB = lancedb.connect(LANCEDB_PATH)

def get_db_table(table_name: str):
    return DB.open_table(table_name)

@app.get("/health")
async def overall_health():
    """Overall system health based on data presence and connectivity."""
    try:
        tbl = get_db_table("movies_real")
        count = tbl.count_rows()
        status = "green" if count > 0 else "red"
        return {"overall_status": status, "movies_count": count, "timestamp": datetime.datetime.now().isoformat()}
    except Exception as e:
        return {"overall_status": "red", "error": str(e)}

@app.get("/quality/report")
async def quality_report():
    """Check LanceDB table metrics."""
    try:
        tbl = get_db_table("movies_real")
        count = tbl.count_rows()
        schema = tbl.schema
        return {
            "status": "passed" if count > 0 else "failed",
            "total_movies": count,
            "columns": schema.names,
            "vector_dimension": len(tbl.head(1)['vector'][0]) if count > 0 else 0
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@app.get("/pipeline/status")
async def pipeline_status():
    """Simple status check."""
    return {"status": "operational", "last_updated": datetime.datetime.now().isoformat()}
