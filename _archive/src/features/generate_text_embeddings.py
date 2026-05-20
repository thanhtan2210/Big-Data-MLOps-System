import os
import logging
import torch
import pandas as pd
import numpy as np
import requests
from typing import List, Tuple, Dict, Any, Optional
from dotenv import load_dotenv
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Tải biến môi trường
load_dotenv()

# ==========================================
# CẤU HÌNH (CONFIGURATIONS) - Sửa lỗi Blocker
# ==========================================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "generate_text_embeddings.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
MOVIES_CSV_PATH: str = os.getenv("MOVIES_CSV", "dataset/ml-25m/movies.csv")
LINKS_CSV_PATH: str = os.getenv("LINKS_CSV", "dataset/ml-25m/links.csv")
OUTPUT_PARQUET_PATH: str = os.getenv("EMBEDDINGS_OUTPUT", "dataset/ml-25m/movie_text_embeddings.parquet")
METADATA_CHECKPOINT: str = "dataset/ml-25m/tmp_movie_metadata.pkl"

MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
MAX_WORKERS: int = int(os.getenv("TMDB_MAX_WORKERS", "20"))
BATCH_SIZE: int = 128

# ==========================================
# CÁC HÀM XỬ LÝ (HELPER FUNCTIONS)
# ==========================================
def get_requests_session() -> requests.Session:
    """Tạo session requests với cơ chế tự động Retry chuyên nghiệp."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def fetch_movie_overview(tmdb_id: float, session: requests.Session) -> Tuple[float, str]:
    """Gọi TMDB API để lấy overview. Sửa lỗi Runtime: Thêm error handling."""
    if pd.isna(tmdb_id) or tmdb_id == 0:
        return tmdb_id, ""
    
    url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}?api_key={TMDB_API_KEY}&language=en-US"
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            return tmdb_id, response.json().get("overview", "")
        return tmdb_id, ""
    except Exception:
        return tmdb_id, ""

def process_tmdb_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sử dụng Multi-threading và Checkpoint. 
    Sửa lỗi High Priority: Chống mất dữ liệu khi crash.
    """
    if os.path.exists(METADATA_CHECKPOINT):
        logger.info(f"Phát hiện checkpoint tại {METADATA_CHECKPOINT}. Đang nạp dữ liệu cũ...")
        return pd.read_pickle(METADATA_CHECKPOINT)

    logger.info(f"Bắt đầu tải metadata từ TMDB cho {len(df)} bộ phim...")
    tmdb_ids = df['tmdbId'].unique()
    overview_map: Dict[float, str] = {}
    
    # Sửa lỗi 🟡: Sử dụng context manager cho session
    with get_requests_session() as session:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_id = {executor.submit(fetch_movie_overview, tid, session): tid for tid in tmdb_ids}
            
            for future in tqdm(as_completed(future_to_id), total=len(future_to_id), desc="TMDB API Progress"):
                t_id, overview = future.result()
                overview_map[t_id] = overview

    df['overview'] = df['tmdbId'].map(overview_map).fillna("")
    
    # Lưu checkpoint
    df.to_pickle(METADATA_CHECKPOINT)
    logger.info(f"Đã lưu checkpoint metadata tại {METADATA_CHECKPOINT}")
    return df

def generate_text_embeddings(texts: List[str]) -> np.ndarray:
    """
    Sử dụng SentenceTransformers với Device Management tường minh.
    Sửa lỗi 🔴: Quản lý GPU/CPU.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Đang sử dụng thiết bị: {device.upper()} để sinh embeddings.")
    
    model = SentenceTransformer(MODEL_NAME, device=device)
    logger.info(f"Đang sinh vector embeddings cho {len(texts)} văn bản...")
    
    embeddings = model.encode(
        texts, 
        show_progress_bar=True, 
        batch_size=BATCH_SIZE,
        convert_to_numpy=True
    )
    return embeddings

# ==========================================
# QUY TRÌNH CHÍNH (MAIN PIPELINE)
# ==========================================
def main() -> None:
    if not TMDB_API_KEY or TMDB_API_KEY == "YOUR_TMDB_API_KEY_HERE":
        logger.error("CẢNH BÁO: TMDB_API_KEY chưa được cấu hình hợp lệ trong file .env")
        return

    try:
        logger.info("1. Đang nạp và tiền xử lý dữ liệu CSV...")
        if not os.path.exists(MOVIES_CSV_PATH) or not os.path.exists(LINKS_CSV_PATH):
            logger.error("Không tìm thấy file CSV đầu vào. Kiểm tra đường dẫn trong .env")
            return

        movies_df = pd.read_csv(MOVIES_CSV_PATH)
        links_df = pd.read_csv(LINKS_CSV_PATH)
        df = pd.merge(movies_df, links_df, on="movieId", how="inner")

        # 2. Lấy Overview (Sửa lỗi High Priority với Checkpoint)
        df = process_tmdb_metadata(df)
        
        logger.info("3. Chuẩn bị nội dung văn bản (Combined Text)...")
        df['clean_genres'] = df['genres'].str.replace("|", " ", regex=False)
        df['combined_text'] = (
            df['title'] + 
            ". Genres: " + df['clean_genres'] + 
            ". Overview: " + df['overview']
        ).fillna("")
        
        # 4. Sinh Embeddings (Sửa lỗi High Priority với Device Management)
        embeddings = generate_text_embeddings(df['combined_text'].tolist())
        df['embedding'] = embeddings.tolist()
        
        logger.info(f"5. Đang lưu kết quả cuối cùng ra Parquet: {OUTPUT_PARQUET_PATH}")
        columns_to_keep = ['movieId', 'imdbId', 'tmdbId', 'title', 'genres', 'overview', 'embedding']
        df[columns_to_keep].to_parquet(OUTPUT_PARQUET_PATH, engine="pyarrow", index=False)
        
        # Xóa checkpoint sau khi hoàn tất thành công
        if os.path.exists(METADATA_CHECKPOINT):
            os.remove(METADATA_CHECKPOINT)
            
        logger.info("HOÀN TẤT: Toàn bộ quy trình sinh embeddings đã thành công!")

    except Exception as e:
        logger.error(f"LỖI NGHIÊM TRỌNG trong Pipeline: {e}")
        raise

if __name__ == "__main__":
    main()
