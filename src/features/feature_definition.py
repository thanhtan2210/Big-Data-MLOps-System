from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64

# 1. Định nghĩa Thực thể (Entities)
#userId = Entity(name="userId", join_keys=["userId"], description="User ID")
#movieId = Entity(name="movieId", join_keys=["movieId"], description="Movie ID")

user_entity = Entity(name="user", join_keys=["userId"])
movie_entity = Entity(name="movie", join_keys=["movieId"])

# 2. Định nghĩa Nguồn dữ liệu (Sources) - Trỏ tới Gold Layer trên MinIO
# Trong môi trường thực tế, Feast sẽ đọc trực tiếp từ Delta Table
user_source = FileSource(
    path="s3a://movie-data/gold/user_features",
    event_timestamp_column="updated_at",
    file_format="parquet" # Delta Lake lưu trữ dưới dạng parquet files
)

movie_source = FileSource(
    path="s3a://movie-data/gold/movie_features",
    event_timestamp_column="updated_at",
    file_format="parquet"
)

# 3. Định nghĩa Feature Views cho User
user_features_view = FeatureView(
    name="user_features",
    entities=[user_entity],
    ttl=timedelta(days=1),
    schema=[
        Field(name="user_avg_rating", dtype=Float32),
        Field(name="user_rating_count", dtype=Int64),
    ],
    online=True,
    source=user_source,
)

# 4. Định nghĩa Feature Views cho Movie
movie_features_view = FeatureView(
    name="movie_features",
    entities=[movie_entity],
    ttl=timedelta(days=1),
    schema=[
        Field(name="movie_avg_rating", dtype=Float32),
        Field(name="movie_rating_count", dtype=Int64),
    ],
    online=True,
    source=movie_source,
)
