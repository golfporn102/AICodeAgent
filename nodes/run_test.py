import json
import subprocess
from google import genai
from config import (MAX_TEST_RETRY,GEMINI_API_KEY,GEMINI_MODEL)
import os
import shutil

client = genai.Client(
    api_key=GEMINI_API_KEY
)

def run_test(state):
    print("run_test")

    project_dir = os.path.abspath(state["project_dir"])
    retry_count = state.get("retry_count", 0)

    mvnw = os.path.join(project_dir, "mvnw.cmd")
    mvn = shutil.which("mvn")

    print("PROJECT DIR:", project_dir)
    print("MAVEN WRAPPER:", mvnw)
    print("WRAPPER EXISTS:", os.path.isfile(mvnw))
    print("MAVEN PATH:", mvn)

    # 1. เลือก Maven command
    if os.path.isfile(mvnw):
        command = ["cmd.exe", "/c", mvnw, "test"]
        print("Using Maven Wrapper")
    elif mvn:
        command = [mvn, "test"]
        print("Using installed Maven")
    else:
        raise RuntimeError(
            "Cannot run Maven tests.\n"
            f"Project directory: {project_dir}\n"
            f"Maven Wrapper not found: {mvnw}\n"
            "Maven is also not installed or not in PATH.\n"
            "Install Maven and configure PATH, or create mvnw.cmd."
        )

    # 2. Run tests
    try:
        result = subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600
        )

        test_output = (
            result.stdout or ""
        ) + "\n" + (
            result.stderr or ""
        )

        test_passed = result.returncode == 0

        if not test_passed:
            retry_count += 1

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        test_output = (
            f"Maven test timed out after 600 seconds.\n"
            f"{stdout}\n{stderr}"
        )

        test_passed = False
        retry_count += 1

    print(f"Test output:\n{test_output}")
    print(f"test_passed: {test_passed}")
    print(f"retry_count: {retry_count}")

    return {
        "test_output": test_output,
        "test_passed": test_passed,
        "retry_count": retry_count
    }

def route_test_result(state):
    print("route_test_result")
    if state["test_passed"]:
        if state["mode_test"] == "SKIP_PLAN":
            return "SKIP_PLAN"
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