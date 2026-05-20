# 06_troubleshooting.md

## 🔴 Out Of Memory (OOM) on Hugging Face
- **Symptom**: The Streamlit app crashes when loading the Analytics tab.
- **Root Cause**: Free RAM on HF Spaces is strictly limited (16GB or less). Loading all 25M rows of `ratings.csv` into Pandas causes memory overflow.
- **Solution**: The `load_core_data()` function uses `nrows=500000` to stream a maximum of 500k rows from R2. This serves as an excellent representative sample for Plotly charts without risking RAM crashes.

## 🔴 Error: LanceError(Schema): No field named movieid
- **Symptom**: Error thrown when executing `table.search().where('"movieId" = 1')`.
- **Root Cause**: The DataFusion SQL parser inside LanceDB automatically lowercases column names, causing a mismatch with the actual case-sensitive schema.
- **Solution**: Switched to **Pandas Filtering**. Load the table into a DataFrame `table.to_pandas()` and apply `df[df["movieId"] == 1]`.

## 🔴 Error: only accept 2-D tensor shape, got: []
- **Symptom**: LanceDB throws a Rust panic error during KNN vector search.
- **Root Cause**: PyArrow incorrectly infers the vector column as a Variable-length list instead of a FixedSizeList during DB creation in Colab.
- **Solution**: Define a strict schema: `pa.list_(pa.float32(), 384)` during `create_table`, and forcefully cast query inputs using `np.array(vec, dtype=np.float32).flatten()`.

## 🔴 Error: TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
- **Root Cause**: The newer `httpx` version (0.28+) renamed the `proxies` parameter to `proxy`, breaking the Groq SDK.
- **Solution**: Strictly pin `httpx==0.27.2` in `requirements.txt`.

## 🔴 Error: Groq RateLimitError
- **Symptom**: The LLM stops responding during traffic spikes.
- **Solution**: Integrated a **Smart Fallback** mechanism in `chatbot.py`. It catches the `RateLimitError` and automatically switches to using the local `SentenceTransformer` to query LanceDB, returning a structured text list of movies to ensure High Availability.