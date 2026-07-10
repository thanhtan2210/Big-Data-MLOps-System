import pytest
from unittest.mock import MagicMock, patch
import datetime
from src.serving.health_monitor import get_overall_health, get_quality_report, get_pipeline_status

@patch("src.serving.health_monitor.get_db_table")
def test_get_overall_health_green(mock_get_db_table):
    # Mock database table to return count > 0
    mock_table = MagicMock()
    mock_table.count_rows.return_value = 100
    mock_get_db_table.return_value = mock_table
    
    health = get_overall_health()
    assert health["overall_status"] == "green"
    assert health["movies_count"] == 100
    assert "timestamp" in health

@patch("src.serving.health_monitor.get_db_table")
def test_get_overall_health_red(mock_get_db_table):
    # Mock table to return count = 0
    mock_table = MagicMock()
    mock_table.count_rows.return_value = 0
    mock_get_db_table.return_value = mock_table
    
    health = get_overall_health()
    assert health["overall_status"] == "red"
    assert health["movies_count"] == 0

@patch("src.serving.health_monitor.get_db_table")
def test_get_overall_health_error(mock_get_db_table):
    # Mock DB table connection error
    mock_get_db_table.side_effect = Exception("DB Connection failed")
    
    health = get_overall_health()
    assert health["overall_status"] == "red"
    assert "error" in health
    assert "DB Connection failed" in health["error"]

@patch("src.serving.health_monitor.get_db_table")
def test_get_quality_report_success(mock_get_db_table):
    mock_table = MagicMock()
    mock_table.count_rows.return_value = 10
    
    # Mock columns/schema names
    mock_table.schema.names = ["movieId", "title", "vector"]
    
    # Mock head(1) returning pyarrow table/row with a vector
    mock_row = MagicMock()
    mock_row.__getitem__.return_value.to_pylist.return_value = [[0.1] * 384]
    mock_table.head.return_value = mock_row
    
    mock_get_db_table.return_value = mock_table
    
    report = get_quality_report()
    assert report["status"] == "passed"
    assert report["total_movies"] == 10
    assert report["columns"] == ["movieId", "title", "vector"]
    assert report["vector_dimension"] == 384

@patch("src.serving.health_monitor.get_db_table")
def test_get_quality_report_failure(mock_get_db_table):
    mock_get_db_table.side_effect = Exception("Fail")
    report = get_quality_report()
    assert report["status"] == "failed"
    assert "error" in report

@patch("src.serving.health_monitor.get_s3_client")
def test_get_pipeline_status_operational(mock_get_s3_client):
    mock_s3 = MagicMock()
    # Mock S3 response
    mock_date = datetime.datetime(2026, 7, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    mock_s3.head_object.return_value = {
        'LastModified': mock_date
    }
    mock_get_s3_client.return_value = mock_s3
    
    status = get_pipeline_status()
    assert status["status"] == "operational"
    assert status["last_updated"] == "2026-07-10 12:00:00"

@patch("src.serving.health_monitor.get_s3_client")
def test_get_pipeline_status_error(mock_get_s3_client):
    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = Exception("S3 bucket not found")
    mock_get_s3_client.return_value = mock_s3
    
    status = get_pipeline_status()
    assert status["status"] == "error"
    assert "S3 bucket not found" in status["message"]
