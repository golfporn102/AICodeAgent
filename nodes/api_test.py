
import json
from pathlib import Path
from datetime import datetime, timezone

import requests

from config import API_BASE_URL, API_TIMEOUT


def api_test(state):
    print("====== api_test ==================", flush=True)

    # --------------------------------------------------
    # 1. กำหนด Project Directory
    # --------------------------------------------------
    project_dir = Path(
        state.get("project_dir", ".")
    ).resolve()

    base_url = (
        state.get("base_url") or API_BASE_URL
    ).rstrip("/")

    # --------------------------------------------------
    # 2. อ่าน API Test Plan จากไฟล์
    # --------------------------------------------------
    plan_file = Path(
        state.get(
            "test_plan_file",
            project_dir / "api_test_plan.json",
        )
    )

    if not plan_file.is_absolute():
        plan_file = project_dir / plan_file

    if not plan_file.exists():
        raise FileNotFoundError(
            f"ไม่พบ API Test Plan: {plan_file}"
        )

    with plan_file.open("r", encoding="utf-8") as file:
        plan_data = json.load(file)

    # รองรับ JSON ที่เป็น list หรือ dict
    if isinstance(plan_data, list):
        tests = plan_data

    elif isinstance(plan_data, dict):
        tests = plan_data.get(
            "tests",
            plan_data.get("test_plan", []),
        )

    else:
        raise ValueError(
            "รูปแบบ api_test_plan.json ไม่ถูกต้อง"
        )

    if not isinstance(tests, list):
        raise ValueError(
            "รายการ API Test Plan ต้องเป็น list"
        )

    print(f"Test Plan: {plan_file}", flush=True)
    print(f"API Test Count: {len(tests)}", flush=True)

    if not tests:
        raise ValueError(
            f"ไม่พบรายการทดสอบในไฟล์: {plan_file}"
        )

    # --------------------------------------------------
    # 3. Execute API Tests
    # --------------------------------------------------
    results = []

    for test in tests:
        method = str(
            test.get("method", "GET")
        ).upper()

        path = str(
            test.get("path", "/")
        ).strip()

        expected_status = test.get("expected_status")
        request_body = test.get("request_body")

        result = {
            "name": test.get(
                "name",
                f"{method} {path}",
            ),
            "method": method,
            "path": path,
            "expected_status": expected_status,
            "actual_status": None,
            "passed": False,
            "error": None,
            "response": None,
        }

        # ตรวจสอบข้อมูลพื้นฐาน
        if not path:
            result["error"] = "API path is empty"
            results.append(result)
            continue

        if method not in (
            "GET", "POST", "PUT",
            "PATCH", "DELETE", "HEAD", "OPTIONS"
        ):
            result["error"] = (
                f"Unsupported HTTP method: {method}"
            )
            results.append(result)
            continue

        # ป้องกัน path variable ที่ยังไม่ได้แทนค่า
        if "{" in path or "}" in path:
            result["error"] = (
                "Unresolved path variable. "
                "Replace it with a real test ID first."
            )
            results.append(result)
            continue

        # ป้องกันการแก้ไขข้อมูลโดยไม่มี expected status
        if (
            method in ("POST", "PUT", "PATCH", "DELETE")
            and expected_status is None
        ):
            result["error"] = (
                "Expected status is not confirmed. "
                "Review the test plan before executing."
            )
            results.append(result)
            continue

        url = f"{base_url}/{path.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                json=(
                    request_body
                    if method in ("POST", "PUT", "PATCH")
                    else None
                ),
                timeout=API_TIMEOUT,
            )

            result["actual_status"] = response.status_code

            try:
                result["response"] = response.json()
            except ValueError:
                result["response"] = response.text[:2000]

            if expected_status is None:
                result["error"] = (
                    "Expected status is not defined; "
                    "the result cannot be confirmed."
                )
            else:
                result["passed"] = (
                    response.status_code == expected_status
                )

        except requests.RequestException as exc:
            result["error"] = str(exc)

        results.append(result)

        print(
            f'{method} {path} -> '
            f'{result["actual_status"]}, '
            f'passed={result["passed"]}',
            flush=True,
        )

    # --------------------------------------------------
    # 4. สรุปผล
    # --------------------------------------------------
    total = len(results)

    passed_count = sum(
        1 for result in results
        if result["passed"]
    )

    failed_count = total - passed_count

    test_passed = (
        total > 0 and failed_count == 0
    )

    output_lines = []

    for result in results:
        output_lines.append(
            f'{result["method"]} {result["path"]}: '
            f'expected={result["expected_status"]}, '
            f'actual={result["actual_status"]}, '
            f'passed={result["passed"]}, '
            f'error={result["error"]}'
        )

    # --------------------------------------------------
    # 5. บันทึก API Test Results ลง JSON
    # --------------------------------------------------
    output_file = Path(
        state.get(
            "api_test_results_file",
            project_dir / "api_test_results.json",
        )
    )

    if not output_file.is_absolute():
        output_file = project_dir / output_file

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "base_url": base_url,
        "test_plan_file": str(plan_file),
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "api_test_passed": test_passed,
        "results": results,
    }

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"API Test Results saved: {output_file}",
        flush=True,
    )

    print(
        f"Summary: total={total}, "
        f"passed={passed_count}, "
        f"failed={failed_count}",
        flush=True,
    )

    # --------------------------------------------------
    # 6. ส่งผลกลับเข้า LangGraph State
    # --------------------------------------------------
    return {
        "api_test_results": results,
        "api_test_passed": test_passed,
        "api_test_output": "\n".join(output_lines),
        "api_test_results_file": str(output_file),
    }