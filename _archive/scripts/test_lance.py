import lancedb
import pandas as pd

try:
    db = lancedb.connect("notebooks/tmp_lancedb/movies.lance")
    tbl = db.open_table("movies")
    print("Table columns:", tbl.schema.names)
    print("Record count:", tbl.count_rows())
except Exception as e:
    print(f"Error: {e}")
