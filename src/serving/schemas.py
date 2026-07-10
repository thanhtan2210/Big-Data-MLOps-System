from pandera import Column, DataFrameSchema, Check

# Schema để validate thông tin phim trả về từ LanceDB / format_result
MovieRecordSchema = DataFrameSchema({
    "movie_id": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    "title": Column(str, nullable=False),
    "genres": Column(str, nullable=True),
    "overview": Column(str, nullable=True),
    "poster_path": Column(str, nullable=True),
    "avg_rating": Column(float, Check.in_range(0.0, 5.0), nullable=False),
    "rating_count": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    "similarity_score": Column(float, Check.in_range(0.0, 1.0), nullable=False),
})

# Schema để validate kết quả sau khi qua tầng Reranker
RerankerOutputSchema = DataFrameSchema({
    "movie_id": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    "title": Column(str, nullable=False),
    "genres": Column(str, nullable=True),
    "overview": Column(str, nullable=True),
    "poster_path": Column(str, nullable=True),
    "avg_rating": Column(float, Check.in_range(0.0, 5.0), nullable=False),
    "rating_count": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    "similarity_score": Column(float, Check.in_range(0.0, 1.0), nullable=False),
    "final_score": Column(float, Check.in_range(0.0, 1.0), nullable=False),
})
