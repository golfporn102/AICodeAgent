import json
import os
import re

from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL


def extract_json(text):
    """Extract JSON from Gemini response."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Gemini response does not contain JSON")

    return json.loads(text[start:end + 1])


def api_test_plan(state):
    print(f"====== api_test_plan ==================")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    project_dir = state["project_dir"]
    endpoints = state.get("api_endpoints", [])
    
    if not endpoints:
        return {
            "test_plan": [],
            "test_plan_file": os.path.join(
                project_dir, "api_test_plan.json"
            )
        }

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
You are a Java Spring Boot API test engineer.

Create an API test plan from the supplied endpoints.

Requirements:
1. Return valid JSON only.
2. Create one test per endpoint as a minimum.
3. Use the endpoint's actual method and path.
4. For POST, PUT and PATCH, use the supplied DTO body as a starting point.
5. Do not invent real IDs, credentials or database records.
6. Use expected_status=null if it cannot be established from the evidence.
7. Mark uncertain assumptions in notes.
8. Include a negative test only when its expected result is supported.
9. Do not execute APIs or modify source code.
10. Include query parameters when the endpoint requires them.
11. For path variables such as {id}, keep the placeholder
    and explain how a valid ID can be obtained.
12. Do not use "string", 0, or other generic placeholders
    as if they were valid business data.
13. Derive expected_status only from controller annotations,
    service logic, or other supplied source evidence.
14. If required information is missing, explain exactly
    what evidence is needed in notes.

JSON format:
{{
  "tests": [
    {{
      "name": "Create user",
      "method": "POST",
      "path": "/users",
      "request_body": {{"name": "test"}},
      "expected_status": null,
      "notes": "Expected status requires confirmation"
    }}
  ]
}}

Endpoint evidence:
{json.dumps(endpoints, ensure_ascii=False, indent=2)}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    print(f"api test planGemini response: {response.text}")
    result = extract_json(response.text)
    tests = result.get("tests", [])

    if not isinstance(tests, list):
        raise ValueError("Test plan 'tests' must be a list")

    # Keep only tests referring to discovered endpoints.


    known_endpoints = {
        (
            str(api.get("method", "")).upper(),
            str(api.get("path", "")).strip()
        )
        for controller in endpoints
        for api in controller.get("apis", [])
    }


    validated_tests = []
    print(f"Known endpoints:", known_endpoints)
    print(f"Gemini tests:", tests)
    for test in tests:
        method = str(test.get("method", "")).upper()
        path = test.get("path", "")

        if (method, path) not in known_endpoints:
            continue

        if method not in {
            "GET", "POST", "PUT", "PATCH", "DELETE"
        }:
            continue

        expected_status = test.get("expected_status")

        if (
            expected_status is not None
            and (
                not isinstance(expected_status, int)
                or not 100 <= expected_status <= 599
            )
        ):
            expected_status = None

        body = test.get("request_body", {})
        if not isinstance(body, dict):
            body = {}

        validated_tests.append({
            "name": str(test.get("name") or f"{method} {path}"),
            "method": method,
            "path": path,
            "request_body": body,
            "expected_status": expected_status,
            "notes": str(test.get("notes", ""))
        })

    output_file = os.path.join(
        project_dir, "api_test_plan.json"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            validated_tests,
            f,
            indent=2,
            ensure_ascii=False
        )
    print(f"API test_plan {validated_tests}")
    print(f"API test plan saved to {output_file}")
    return {
        "test_plan": validated_tests,
        "test_plan_file": output_file
    }