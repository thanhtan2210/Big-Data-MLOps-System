import pytest
import numpy as np
from typing import List, Dict, Any

@pytest.fixture
def mock_movie_candidates() -> List[Dict[str, Any]]:
    return [
        {
            "movie_id": 1,
            "title": "Movie A",
            "genres": "Action|Sci-Fi",
            "overview": "Overview A",
            "poster_path": "/pathA.jpg",
            "avg_rating": 4.5,
            "rating_count": 1000,
            "similarity_score": 0.9
        },
        {
            "movie_id": 2,
            "title": "Movie B",
            "genres": "Drama",
            "overview": "Overview B",
            "poster_path": "/pathB.jpg",
            "avg_rating": 3.0,
            "rating_count": 100,
            "similarity_score": 0.8
        },
        {
            "movie_id": 3,
            "title": "Movie C",
            "genres": "Comedy",
            "overview": "Overview C",
            "poster_path": "/pathC.jpg",
            "avg_rating": 5.0,
            "rating_count": 50,
            "similarity_score": 0.95
        }
    ]

@pytest.fixture
def sample_384d_vector() -> np.ndarray:
    vec = np.random.rand(384)
    return vec / np.linalg.norm(vec)
