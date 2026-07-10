import pytest
from src.serving.semantic_search import Reranker

def test_rerank_empty_candidates():
    assert Reranker.rerank([]) == []

def test_rerank_logic(mock_movie_candidates):
    # Rerank with default weights: sim_weight=0.6, pop_weight=0.3, qual_weight=0.1
    # Max pop is 1000 (Movie A)
    # Movie A: sim=0.9, pop=1000/1000=1.0, qual=4.5/5.0=0.9 -> score = 0.9*0.6 + 1.0*0.3 + 0.9*0.1 = 0.54 + 0.30 + 0.09 = 0.93
    # Movie B: sim=0.8, pop=100/1000=0.1, qual=3.0/5.0=0.6 -> score = 0.8*0.6 + 0.1*0.3 + 0.6*0.1 = 0.48 + 0.03 + 0.06 = 0.57
    # Movie C: sim=0.95, pop=50/1000=0.05, qual=5.0/5.0=1.0 -> score = 0.95*0.6 + 0.05*0.3 + 1.0*0.1 = 0.57 + 0.015 + 0.1 = 0.685
    
    # Expected order: Movie A (0.93), Movie C (0.685), Movie B (0.57)
    reranked = Reranker.rerank(mock_movie_candidates)
    
    assert len(reranked) == 3
    assert reranked[0]["title"] == "Movie A"
    assert reranked[1]["title"] == "Movie C"
    assert reranked[2]["title"] == "Movie B"
    
    # Verify final scores exist
    assert "final_score" in reranked[0]
    assert reranked[0]["final_score"] == pytest.approx(0.93)
    assert reranked[1]["final_score"] == pytest.approx(0.685)
    assert reranked[2]["final_score"] == pytest.approx(0.57)

def test_rerank_custom_weights(mock_movie_candidates):
    # Custom weights: sim_weight=1.0, pop_weight=0.0, qual_weight=0.0
    # Should sort purely by similarity_score: Movie C (0.95), Movie A (0.9), Movie B (0.8)
    reranked = Reranker.rerank(mock_movie_candidates, sim_weight=1.0, pop_weight=0.0, qual_weight=0.0)
    
    assert reranked[0]["title"] == "Movie C"
    assert reranked[1]["title"] == "Movie A"
    assert reranked[2]["title"] == "Movie B"
