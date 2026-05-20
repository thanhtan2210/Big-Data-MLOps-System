import requests
import json
import logging
from typing import Dict, Any

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:3000"
TIMEOUT = 30  # Timeout cho các yêu cầu API (Gemini có thể chậm)

def call_api(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Hàm helper để gọi API với xử lý lỗi timeout và exception."""
    url = f"{BASE_URL}{endpoint}"
    try:
        logger.info(f"Calling {endpoint} with payload: {payload}")
        response = requests.post(url, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout error: API {endpoint} took longer than {TIMEOUT}s")
        return {"status": "error", "message": "timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        return {"status": "error", "message": str(e)}

def test_recommendation_endpoint():
    """Test 1: Kiểm tra gợi ý phim cá nhân hóa."""
    logger.info("--- Testing POST /recommend ---")
    payload = {"user_id": 123}
    result = call_api("/recommend", payload)
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    assert result.get("status") == "success"

def test_chat_endpoint():
    """Test 2: Kiểm tra AI Chatbot tìm phim."""
    logger.info("--- Testing POST /chat ---")
    payload = {
        "message": "Hãy gợi ý cho tôi vài bộ phim khoa học viễn tưởng giống Matrix",
        "session_id": "test_session_01"
    }
    result = call_api("/chat", payload)
    print(f"AI Response: {result.get('response')}")
    assert result.get("status") == "success"

def test_session_isolation():
    """
    Test 3: Kiểm tra tính Session Isolation (Stateless).
    Gửi 2 request với 2 session khác nhau để đảm bảo bot không bị nhầm lẫn ngữ cảnh.
    """
    logger.info("--- Testing Session Isolation ---")
    
    # Request từ User A (Nam)
    payload_a = {
        "message": "Tôi tên là Nam. Tôi thích phim hành động. Hãy nhớ tên tôi nhé.",
        "session_id": "nam_session_123"
    }
    res_a = call_api("/chat", payload_a)
    logger.info(f"User Nam Response: {res_a.get('response')[:100]}...")

    # Request từ User B (Hoa) - Ngay lập tức
    payload_b = {
        "message": "Tôi tên là Hoa. Bạn có biết tôi thích phim gì không? (Đừng nhầm tôi với người khác)",
        "session_id": "hoa_session_456"
    }
    res_b = call_api("/chat", payload_b)
    logger.info(f"User Hoa Response: {res_b.get('response')[:100]}...")

    # Kiểm tra xem AI có nhầm Hoa thành Nam không
    response_text = res_b.get('response', '').lower()
    if "nam" in response_text:
        logger.error("❌ FAILED: Session Isolation bị lỗi! AI đã nhầm Hoa thành Nam.")
    else:
        logger.info("✅ SUCCESS: Session Isolation hoạt động tốt. AI không bị nhầm lẫn ngữ cảnh.")

if __name__ == "__main__":
    logger.info("🚀 Starting Serving Layer Integration Tests...")
    
    # Kiểm tra xem server có đang chạy không
    try:
        requests.get(BASE_URL, timeout=5)
    except:
        logger.error(f"🚨 Server BentoML chưa chạy tại {BASE_URL}. Hãy chạy 'bentoml serve' trước.")
        # Chúng ta không exit ở đây để pytest có thể báo lỗi một cách chính thống nếu dùng pytest runner
        
    test_recommendation_endpoint()
    print("\n")
    test_chat_endpoint()
    print("\n")
    test_session_isolation()
    
    logger.info("="*50)
    logger.info("INTEGRATION TESTS COMPLETED")
    logger.info("="*50)
