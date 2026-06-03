import os
import logging
import bentoml
import mlflow
import pydantic
import json
import hashlib
import time
import numpy as np
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import redis

# Import module Chatbot đã được fix ở bước trước
try:
    from src.serving.chatbot import MovieChatbot
except ImportError:
    MovieChatbot = None

# Tải biến môi trường
load_dotenv(override=True)

# ==========================================
# CẤU HÌNH LOGGING
# ==========================================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Cấu hình Logging chuyên nghiệp của BentoML
logger = logging.getLogger("bentoml.movie_service")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "service.log"))
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# ==========================================
# KHAI BÁO CẤU TRÚC DỮ LIỆU
# ==========================================
class RecommendRequest(pydantic.BaseModel):
    user_id: int = pydantic.Field(..., gt=0,
                                  description="ID của người dùng, phải lớn hơn 0")

class RecommendRequestWrapper(pydantic.BaseModel):
    request: RecommendRequest

class ChatRequest(pydantic.BaseModel):
    message: str = pydantic.Field(..., min_length=1)
    session_id: str = pydantic.Field(
        "default_user", description="ID phiên làm việc để quản lý lịch sử chat")
    history: Optional[List[Dict[str, Any]]] = None

class ChatRequestWrapper(pydantic.BaseModel):
    request: ChatRequest

# ==========================================
# BENTOML SERVICE DEFINITION
# ==========================================

@bentoml.service(
    name="movie_recommender_service",
    traffic={"timeout": 60},
)
class MovieRecommenderService:
    def __init__(self):
        """
        Khởi tạo Service: Kết nối hạ tầng Docker, nạp Model, Feast, LanceDB và Redis.
        """
        logger.info("Initializing Movie Recommender Service...")

        # 1. Cấu hình MLflow
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow.set_tracking_uri(mlflow_uri)
        os.environ['MLFLOW_S3_ENDPOINT_URL'] = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        os.environ['AWS_ACCESS_KEY_ID'] = os.getenv("MINIO_ACCESS_KEY", "admin")
        os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv("MINIO_SECRET_KEY", "password")

        model_name = os.getenv("MODEL_NAME", "user_tower_model")
        model_version = None  
        
        try:
            from mlflow.tracking import MlflowClient
            import tensorflow as tf
            client = MlflowClient(tracking_uri=mlflow_uri)
            model_versions = client.get_latest_versions(model_name, stages=["Production"])
            
            if model_versions:
                model_version = model_versions[0].version
                logger.info(f"Using {model_name} version {model_version}")
            else:
                logger.warning(f"No Production model found, using latest")
                model_versions = client.get_latest_versions(model_name)
                model_version = model_versions[0].version if model_versions else None
            
            if model_version:
                model_uri = f"models:/{model_name}/{model_version}"
                artifact_path = mlflow.artifacts.download_artifacts(artifact_uri=model_uri)
                saved_model_path = os.path.join(artifact_path, "data", "model")
                if not os.path.exists(saved_model_path):
                    saved_model_path = os.path.join(artifact_path, "data")
                    if not os.path.exists(saved_model_path):
                         saved_model_path = artifact_path
                
                self.user_tower = tf.saved_model.load(saved_model_path)
                logger.info(f"✅ Model loaded from {saved_model_path}")
                self.model_ready = True
            else:
                raise ValueError("No model version found in registry")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            self.user_tower = None
            self.model_ready = False

        # 2. Khởi tạo Feast Feature Store
        try:
            from feast import FeatureStore
            feast_repo_path = os.getenv("FEAST_REPO_PATH", "./feast_repo")
            if os.path.exists(feast_repo_path) or os.path.exists(os.path.join(feast_repo_path, "feature_store.yaml")):
                self.fs = FeatureStore(repo_path=feast_repo_path)
                logger.info(f"✅ Feast Feature Store initialized from {feast_repo_path}")
            else:
                logger.warning(f"⚠️ Feast repo path {feast_repo_path} does not exist or missing feature_store.yaml.")
                self.fs = None
        except Exception as e:
            logger.warning(f"⚠️ Feast initialization failed: {e}")
            self.fs = None

        # 3. Khởi tạo LanceDB (Semantic Search Engine)
        try:
            from src.serving.semantic_search import SemanticSearchEngine
            lancedb_uri = os.getenv("LANCEDB_URI", "notebooks/tmp_lancedb")
            self.lancedb_engine = SemanticSearchEngine(lancedb_uri=lancedb_uri)
            self.lancedb_engine.load_table()
            self.lancedb_ready = True
            logger.info("✅ LanceDB engine initialized and table loaded.")
        except Exception as e:
            logger.warning(f"⚠️ LanceDB init failed: {e}")
            self.lancedb_engine = None
            self.lancedb_ready = False

        # 4. Khởi tạo Redis Cache
        try:
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.cache_ttl = int(os.getenv("CACHE_TTL_SECONDS", 3600))
            logger.info("✅ Redis cache connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable: {e}. Using in-memory cache")
            self.redis_client = None
            self.in_memory_cache = {}
            self.cache_ttl = 3600

        # 5. Khởi tạo Gemini Chatbot
        if MovieChatbot:
            try:
                self.chatbot = MovieChatbot()
                logger.info("✅ MovieChatbot initialized successfully.")
            except Exception as e:
                logger.error(f"⚠️ Error initializing Chatbot: {e}")
                self.chatbot = None
        else:
            self.chatbot = None

    def _get_cache_key(self, **kwargs) -> str:
        """Sinh ra khóa cache độc nhất dựa trên tham số"""
        key_str = json.dumps(kwargs, sort_keys=True, default=str)
        return f"rec:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    def _cache_recommendation(self, user_id: int, recommendations: List[Dict]):
        """Lưu kết quả gợi ý vào Cache"""
        cache_key = self._get_cache_key(user_id=user_id, type="recommend")
        try:
            if self.redis_client:
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(recommendations)
                )
            else:
                self.in_memory_cache[cache_key] = {
                    "data": recommendations,
                    "expire_at": time.time() + self.cache_ttl
                }
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def _get_cached_recommendation(self, user_id: int) -> Optional[List[Dict]]:
        """Lấy kết quả từ Cache nếu có"""
        cache_key = self._get_cache_key(user_id=user_id, type="recommend")
        try:
            if self.redis_client:
                cached = self.redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache HIT for user_id: {user_id}")
                    return json.loads(cached)
            else:
                if cache_key in self.in_memory_cache:
                    entry = self.in_memory_cache[cache_key]
                    if time.time() < entry.get("expire_at", 0):
                        logger.info(f"Memory Cache HIT for user_id: {user_id}")
                        return entry["data"]
                    else:
                        del self.in_memory_cache[cache_key]
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        return None

    def _get_user_features(self, user_id: int) -> np.ndarray:
        """Lấy feature của người dùng từ Feast"""
        try:
            if self.fs:
                feature_refs = [
                    "user_features:user_avg_rating",
                    "user_features:user_rating_count"
                ]
                # Entity dict keys must match entity definition in feature_definition.py
                features_df = self.fs.get_online_features(
                    features=feature_refs,
                    entity_rows=[{"userId": user_id}]
                ).to_dict()
                
                # Handling lists returned by to_dict()
                user_avg_rating = features_df.get("user_avg_rating", [0.5])[0]
                user_rating_count = features_df.get("user_rating_count", [10.0])[0]
                
                # Check for None values (missing features)
                if user_avg_rating is None: user_avg_rating = 0.5
                if user_rating_count is None: user_rating_count = 10.0
                
                user_features = np.array([user_avg_rating, user_rating_count], dtype=np.float32)
                logger.info(f"Fetched features from Feast for user {user_id}: {user_features}")
                return user_features
            else:
                logger.warning("Feast unavailable, using default features")
                return np.array([0.5, 10.0], dtype=np.float32)
        except Exception as e:
            logger.error(f"Feature fetch error: {e}")
            return np.array([0.5, 10.0], dtype=np.float32)

    def _get_user_embedding(self, user_features: np.ndarray) -> np.ndarray:
        """Tạo embedding cho người dùng thông qua mô hình TensorFlow"""
        try:
            import tensorflow as tf
            # Trreshape to batch size 1
            user_features_input = user_features.reshape(1, -1).astype(np.float32)
            
            # Cố gắng invoke theo nhiều format (Dict vs Tensor)
            try:
                # Nếu signature là dict
                user_embedding, _ = self.user_tower({'user_features': user_features_input}, training=False)
            except:
                # Nếu signature là tensor direct
                user_embedding = self.user_tower(user_features_input)
            
            # Nếu trả về tuple, lấy phần tử đầu tiên
            if isinstance(user_embedding, tuple) or isinstance(user_embedding, list):
                user_embedding = user_embedding[0]
                
            # L2 Normalize
            user_embedding = tf.nn.l2_normalize(user_embedding, axis=1).numpy()
            return user_embedding[0]
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            # Fallback random vector if model fails to predict
            return np.random.rand(64).astype(np.float32)

    def _search_similar_movies(self, user_embedding: np.ndarray, top_k: int = 10) -> List[Dict]:
        """Tìm kiếm phim tương đồng từ LanceDB"""
        try:
            if not self.lancedb_ready:
                logger.warning("LanceDB not available, returning fallback")
                return self._get_fallback_recommendations()
            
            query_embedding = user_embedding.tolist()
            
            results_df = self.lancedb_engine.table.search(query_embedding) \
                .metric("cosine") \
                .limit(top_k) \
                .to_pandas()
            
            recommendations = []
            for _, row in results_df.iterrows():
                recommendations.append({
                    "movie_id": int(row["movieId"]),
                    "title": row.get("title", f"Movie {row['movieId']}"),
                    "genres": row.get("genres", ""),
                    "score": float(round(1.0 - row.get("_distance", 0.5), 4))
                })
            
            logger.info(f"Found {len(recommendations)} similar movies from LanceDB.")
            return recommendations
            
        except Exception as e:
            logger.error(f"LanceDB search error: {e}")
            return self._get_fallback_recommendations()

    def _get_fallback_recommendations(self) -> List[Dict]:
        return [
            {"movie_id": 101, "title": "The Shawshank Redemption", "score": 0.98},
            {"movie_id": 102, "title": "The Godfather", "score": 0.96}
        ]

    @bentoml.api
    def recommend(self, request: RecommendRequestWrapper) -> Dict[str, Any]:
        """
        Endpoint 1: Gợi ý phim cá nhân hóa.
        """
        user_id = request.request.user_id
        logger.info(f"[/recommend] Processing user_id: {user_id}")

        if not self.model_ready:
             logger.warning("Model is not ready, will use random embedding fallback")

        try:
            # 1. Kiểm tra Cache
            cached_result = self._get_cached_recommendation(user_id)
            if cached_result:
                return {
                    "user_id": user_id,
                    "recommendations": cached_result,
                    "status": "success",
                    "source": "cache"
                }

            # 2. Fetch User Features (Feast)
            user_features = self._get_user_features(user_id)
            
            # 3. Predict ra User Vector (MLflow/TF)
            if self.model_ready:
                user_vector = self._get_user_embedding(user_features)
            else:
                user_vector = np.random.rand(64).astype(np.float32)
                
            # 4. Tìm kiếm ngữ nghĩa bằng LanceDB
            recommendations = self._search_similar_movies(user_vector, top_k=10)

            # 5. Lưu vào Cache
            if recommendations:
                self._cache_recommendation(user_id, recommendations)

            return {
                "user_id": user_id,
                "recommendations": recommendations,
                "status": "success",
                "source": "computed"
            }
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện recommend: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @bentoml.api
    def chat(self, request: ChatRequestWrapper) -> Dict[str, Any]:
        """
        Endpoint 2: AI Chatbot. 
        """
        if not self.chatbot:
            return {
                "response": "Hệ thống Chat hiện không khả dụng (thiếu cấu hình API Key).",
                "status": "error"
            }

        chat_req = request.request
        logger.info(
            f"[/chat] Session: {chat_req.session_id} - Message: {chat_req.message}")

        try:
            bot_response = self.chatbot.chat(
                user_message=chat_req.message,
                history=chat_req.history
            )

            return {
                "response": bot_response,
                "session_id": chat_req.session_id,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Lỗi xử lý Chat: {e}")
            return {
                "response": "Tôi gặp chút khó khăn khi suy nghĩ. Thử lại sau nhé!",
                "status": "error"
            }

    @bentoml.api
    def health(self) -> Dict[str, bool]:
        """Endpoint kiểm tra sức khỏe hệ thống."""
        return {
            "model_loaded": self.model_ready,
            "chatbot_ready": self.chatbot is not None,
            "feast_ready": self.fs is not None,
            "lancedb_ready": self.lancedb_ready,
            "redis_ready": self.redis_client is not None
        }