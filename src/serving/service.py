import bentoml
from bentoml.io import JSON, Text
import numpy as np
import lancedb
import feast
import os

# 1. Khởi tạo kết nối tới Feature Store (Feast)
# fs = feast.FeatureStore(repo_path="src/features")

# 2. Khởi tạo kết nối tới Vector DB (LanceDB)
# db = lancedb.connect("s3a://movie-data/lancedb") # Lưu trữ trên MinIO
# table = db.open_table("movie_embeddings")

# Định nghĩa BentoML Service
@bentoml.service(
    name="movie_recommender_service",
    traffic={"timeout": 60},
)
class MovieRecommenderService:
    def __init__(self):
        # Trong thực tế, sẽ tải model từ BentoML Model Store (đã import từ MLflow)
        print("Loading models and connecting to databases...")
        self.user_tower = None # Placeholder cho User Tower model
        
    @bentoml.api
    def recommend(self, user_id: str) -> dict:
        """
        Endpoint gợi ý phim cho người dùng
        """
        # BƯỚC 1: Lấy đặc trưng User từ Feast (Online Store - Redis)
        # user_features = fs.get_online_features(
        #     features=["user_features:user_avg_rating", "user_features:user_rating_count"],
        #     entity_rows=[{"userId": int(user_id)}]
        # ).to_dict()
        
        # BƯỚC 2: Tạo User Embedding (Sử dụng User Tower Model)
        # mock_features = np.array([[user_features['user_avg_rating'][0], user_features['user_rating_count'][0]]])
        # user_embedding = self.user_tower.predict(mock_features)
        
        # BƯỚC 3: Tìm kiếm Vector ứng viên trong LanceDB (Retrieval)
        # results = table.search(user_embedding).limit(10).to_pandas()
        
        # Mock response cho demo
        mock_recommendations = [
            {"movie_id": 1, "score": 0.95, "title": "Toy Story (1995)"},
            {"movie_id": 2, "score": 0.92, "title": "Jumanji (1995)"},
            {"movie_id": 3, "score": 0.88, "title": "Heat (1995)"}
        ]
        
        return {
            "user_id": user_id,
            "recommendations": mock_recommendations,
            "status": "success"
        }

if __name__ == "__main__":
    # Test service locally
    svc = MovieRecommenderService()
    print(svc.recommend("101"))
