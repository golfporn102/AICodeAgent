import requests
from config import API_BASE_URL, API_TIMEOUT


def api_test(state):
    print(f"====== api_test ==================")
    base_url = (
        state.get("base_url") or API_BASE_URL
    ).rstrip("/")

    tests = state.get("test_plan", [])
    results = []

    for test in tests:
        method = test.get("method", "GET").upper()
        path = test.get("path", "/")
        expected_status = test.get("expected_status")
        request_body = test.get("request_body")

        result = {
            "name": test.get("name", f"{method} {path}"),
            "method": method,
            "path": path,
            "expected_status": expected_status,
            "actual_status": None,
            "passed": False,
            "error": None,
            "response": None
        }

        # Prevent unresolved path variables from being sent.
        if "{" in path or "}" in path:
            result["error"] = (
                "Unresolved path variable. "
                "Replace it with a real test ID first."
            )
            results.append(result)
            continue

        # Do not send a mutating request without a confirmed
        # expectation. This avoids blind writes.
        if (
            method in ("POST", "PUT", "PATCH", "DELETE")
            and expected_status is None
        ):
            result["error"] = (
                "Expected status is not confirmed. "
                "Review the test plan before executing this "
                "mutating request."
            )
            results.append(result)
            continue

        try:
            response = requests.request(
                method=method,
                url=f"{base_url}/{path.lstrip('/')}",
                json=(
                    request_body
                    if method in ("POST", "PUT", "PATCH")
                    else None
                ),
                timeout=API_TIMEOUT
            )

            result["actual_status"] = response.status_code

            try:
                result["response"] = response.json()
            except ValueError:
                result["response"] = response.text[:2000]

            if expected_status is None:
                result["error"] = (
                    "Expected status is not defined; "
                    "the test result cannot be confirmed."
                )
            else:
                result["passed"] = (
                    response.status_code == expected_status
                )

        except requests.RequestException as exc:
            result["error"] = str(exc)

        results.append(result)

    test_passed = bool(results) and all(
        result["passed"] for result in results
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

    return {
        "api_test_results": results,
        "api_test_passed": test_passed,
        "api_test_output": "\n".join(output_lines)
    }