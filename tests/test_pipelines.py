import pytest
from pyspark.sql import Row
from src.utils.spark_session import get_spark_session
from pyspark.sql import functions as F

@pytest.fixture(scope="module")
def spark():
    """ Khởi tạo Spark Session dùng chung cho các test case """
    spark = get_spark_session("Unit-Test-Pipelines")
    yield spark
    spark.stop()

def test_data_cleansing_logic(spark):
    """ 
    Test case kiểm tra logic làm sạch dữ liệu:
    1. Loại bỏ Rating ngoài khoảng [0, 5]
    2. Loại bỏ dữ liệu Null
    """
    
    # 1. Tạo dữ liệu giả lập (Mock data)
    data = [
        Row(userId=1, movieId=101, rating=4.5, timestamp=123456), # Hợp lệ
        Row(userId=2, movieId=102, rating=6.0, timestamp=123457), # Sai (rating > 5)
        Row(userId=None, movieId=103, rating=3.0, timestamp=123458), # Sai (null user)
        Row(userId=3, movieId=104, rating=-1.0, timestamp=123459), # Sai (rating < 0)
    ]
    
    df = spark.createDataFrame(data)
    
    # 2. Áp dụng logic làm sạch (copy từ bronze_to_silver.py)
    df_cleaned = df.filter(F.col("userId").isNotNull() & F.col("movieId").isNotNull()) \
                   .filter((F.col("rating") >= 0) & (F.col("rating") <= 5))
    
    # 3. Kiểm tra kết quả (Assert)
    results = df_cleaned.collect()
    
    assert len(results) == 1
    assert results[0]['userId'] == 1
    assert results[0]['rating'] == 4.5
    print("\n✅ Spark Cleansing Logic Test: PASSED")

def test_feature_aggregation(spark):
    """
    Test case kiểm tra logic tính toán đặc trưng (Aggregation)
    """
    data = [
        Row(userId=1, rating=4.0),
        Row(userId=1, rating=5.0),
        Row(userId=2, rating=3.0),
    ]
    df = spark.createDataFrame(data)
    
    # Tính trung bình rating theo user
    user_features = df.groupBy("userId").agg(F.avg("rating").alias("avg_rating"))
    
    results = user_features.collect()
    
    # Kiểm tra User 1 có trung bình là 4.5
    user1_avg = [r['avg_rating'] for r in results if r['userId'] == 1][0]
    assert user1_avg == 4.5
    print("✅ Feature Aggregation Test: PASSED")
