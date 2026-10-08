import json
import subprocess
from google import genai
from config import (MAX_TEST_RETRY,GEMINI_API_KEY,GEMINI_MODEL)
import os

client = genai.Client(
    api_key=GEMINI_API_KEY
)

def run_test(state):
    print("run_test")
    project_dir = state["project_dir"]

    retry_count = state.get("retry_count", 0)
    mvnw = os.path.join(project_dir, "mvnw.cmd")

    print("PROJECT DIR:", project_dir)
    print("MAVEN WRAPPER:", mvnw)
    print("EXISTS:", os.path.exists(mvnw))

    if not os.path.exists(mvnw):
        raise RuntimeError(
            f"mvnw.cmd not found: {mvnw}"
        )

    result = subprocess.run(
        [mvnw, "test"],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    test_output = result.stdout + "\n" + result.stderr

    if result.returncode == 0:
        test_passed = True
    else:
        test_passed = False
        retry_count += 1

    print(f"Test output:\n{test_output}")
    print(f"test_passed:\n{test_passed}")
    print(f"Retry_count:\n{retry_count}")
    return {
        "test_output": test_output,
        "test_passed": test_passed,
        "retry_count": retry_count
    }

def route_test_result(state):
    print("route_test_result")
    if state["test_passed"]:
        return "PASS"
    
    if state["retry_count"] >= MAX_TEST_RETRY:
        return "MAX_RETRY"

    return "FAIL"

def analyze_test_failure(state):
    print("analyze_test_failure")
    test_output = state.get("test_output", "")
    project_context = state.get("project_context", "")

    prompt = f"""
You are a Java Spring Boot test failure analyzer.

Analyze the test failure below.

Test output:
{test_output}

Relevant source code:
{project_context}

Determine the most likely cause.

Possible actions:

- FIX_CODE
  The production code is incorrect and should be fixed.

- FIX_TEST
  The Unit Test is incorrect, outdated, or has an incorrect expectation.

- UNKNOWN
  There is not enough information to determine the cause.

Return ONLY valid JSON:

{{
    "fix_action": "FIX_CODE",
    "fix_reason": "UserService returns incorrect result when user does not exist."
}}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json"
        }
    )

    result = json.loads(response.text)
    print(f"result: {result}")
    
   
    return {
        "fix_action": result["fix_action"],
        "fix_reason": result["fix_reason"]
    }