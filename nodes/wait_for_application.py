import time
import requests
from config import API_BASE_URL


def wait_for_application(state):
    print(f"====== wait_for_application ==================")
    base_url = (
        state.get("base_url") or API_BASE_URL
    ).rstrip("/")

    # ปรับตาม Health endpoint ของโปรเจกต์
    health_url = base_url + "/actuator/health"

    for _ in range(30):
        try:
            response = requests.get(
                health_url,
                timeout=2
            )

            if response.status_code == 200:
                return {"app_started": True}

        except requests.RequestException:
            pass

        time.sleep(2)

    raise TimeoutError(
        f"Spring Boot ไม่พร้อมใช้งาน: {health_url}"
    )