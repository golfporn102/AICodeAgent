import json
from pathlib import Path
from urllib.parse import urlsplit


def normalize_path(path):
    path = str(path or "").strip()

    # รองรับ URL เต็มและ path ปกติ
    if path.startswith(("http://", "https://")):
        path = urlsplit(path).path

    if path != "/":
        path = path.rstrip("/")

    return path


def get_request_path(request):
    url = request.get("url", "")

    # Postman Collection v2.1 อาจเก็บ URL เป็น object
    if isinstance(url, dict):
        path = url.get("path", [])

        if isinstance(path, list):
            return "/" + "/".join(
                str(part) for part in path
            )

        return normalize_path(path)

    # รองรับ URL แบบ string
    return normalize_path(url)


def set_postman_values(state):
    print(f"====== set_postman_values ==================")
    project_dir = Path(state.get("project_dir", ".")).resolve()

    # อ่านไฟล์จาก state ก่อน ถ้าไม่มีใช้ path เริ่มต้น
    test_plan_file = Path(
        state.get("test_plan_file", project_dir / "api_test_plan.json")
    )

    collection_file = Path(
        state.get(
            "postman_collection_file",
            project_dir / "postman_collection.json"
        )
    )

    if not test_plan_file.is_absolute():
        test_plan_file = project_dir / test_plan_file

    if not collection_file.is_absolute():
        collection_file = project_dir / collection_file

    if not test_plan_file.exists():
        raise FileNotFoundError(
            f"ไม่พบ Test Plan: {test_plan_file}"
        )

    if not collection_file.exists():
        raise FileNotFoundError(
            f"ไม่พบ Postman Collection: {collection_file}"
        )

    # 1. อ่าน Test Plan
    with test_plan_file.open("r", encoding="utf-8") as f:
        plan_data = json.load(f)

    if isinstance(plan_data, list):
        tests = plan_data
    elif isinstance(plan_data, dict):
        tests = plan_data.get("tests", [])
    else:
        raise ValueError("รูปแบบ api_test_plan.json ไม่ถูกต้อง")

    if not tests:
        raise ValueError("ไม่พบ tests ใน api_test_plan.json")

    # 2. อ่าน Postman Collection
    with collection_file.open("r", encoding="utf-8") as f:
        collection = json.load(f)

    # จับคู่ด้วย method + path
    test_map = {}

    for test in tests:
        method = str(test.get("method", "GET")).upper()
        path = normalize_path(test.get("path", ""))

        if not path:
            continue

        test_map.setdefault((method, path), []).append(test)

    updated = 0

    def update_items(items):
        nonlocal updated

        for item in items:
            # รองรับ folder ที่มี request ซ้อนอยู่
            if "item" in item:
                update_items(item["item"])
                continue

            request = item.get("request")

            if not isinstance(request, dict):
                continue

            method = str(request.get("method", "GET")).upper()
            path = get_request_path(request)

            candidates = test_map.get((method, path), [])

            if not candidates:
                continue

            # ใช้ test case แรกที่ยังไม่ได้จับคู่
            test = candidates.pop(0)

            # ใส่ request body
            body = test.get("request_body")

            if method in {"POST", "PUT", "PATCH"} and isinstance(body, dict):
                request["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(
                        body,
                        ensure_ascii=False,
                        indent=2
                    ),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                }

                headers = request.setdefault("header", [])

                if not any(
                    h.get("key", "").lower() == "content-type"
                    for h in headers
                ):
                    headers.append({
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    })

            # เก็บ expected status และ notes ไว้ในชื่อ request
            # เพื่อช่วยตรวจสอบ test case ภายหลัง
            item["name"] = test.get("name", item.get("name", "API Test"))

            updated += 1

    update_items(collection.get("item", []))

    # 3. บันทึก Collection กลับลงไฟล์
    with collection_file.open("w", encoding="utf-8") as f:
        json.dump(
            collection,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Updated Postman requests: {updated}")
    print(f"Collection saved: {collection_file}")

    return {
        "postman_collection_file": str(collection_file),
        "postman_requests_updated": updated
    }
