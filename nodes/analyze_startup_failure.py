import json
from pathlib import Path

from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_STARTUP_RETRY


client = genai.Client(api_key=GEMINI_API_KEY)


def analyze_startup_failure(state):
    print("====== analyze_startup_failure ======", flush=True)

    project_dir = Path(state["project_dir"]).resolve()

    # 1. อ่าน application.log
    log_path = Path(
        state.get("app_log_file", project_dir / "application.log")
    )

    if not log_path.is_absolute():
        log_path = project_dir / log_path

    if log_path.exists():
        log_text = log_path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    else:
        log_text = "application.log not found"

    # จำกัด log เพื่อไม่ให้ส่ง Token มากเกินไป
    log_text = log_text[-15000:]

    # 2. นับจำนวนครั้งที่ Startup ล้มเหลว
    retry_count = state.get("startup_retry_count", 0) + 1

    # 3. เตรียมข้อมูลให้ Gemini วิเคราะห์
    project_context = state.get("project_context", "")

    prompt = f"""
You are a Java Spring Boot startup failure analyzer.

Analyze the startup error and determine the root cause.

PROJECT DIRECTORY:
{project_dir}

STARTUP ERROR LOG:
{log_text}

RELEVANT SOURCE CODE:
{project_context}

Return ONLY valid JSON with this structure:
{{
    "fix_action": "FIX_CODE",
    "fix_reason": "Explain the root cause",
    "files_to_fix": ["src/main/java/example/Example.java"]
}}

Allowed fix_action values:
- FIX_CODE: Source code or project configuration must be changed.
- ENVIRONMENT: The issue is caused by the environment, port, database,
  missing environment variables, or external dependencies.
- UNKNOWN: The root cause cannot be determined.

Rules:
1. Identify the root cause from the actual log.
2. Do not invent file paths or class names.
3. Prefer modifying existing files over creating duplicate classes.
4. Preserve existing business logic and security configuration.
5. Do not remove security features to make the application start.
6. Do not modify Java code for a port conflict or unavailable database.
7. If files_to_fix cannot be determined, return an empty list.
8. Return JSON only, without Markdown.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        result = json.loads(response.text)

        fix_action = result.get("fix_action", "UNKNOWN")
        fix_reason = result.get("fix_reason", "")
        files_to_fix = result.get("files_to_fix", [])

        if fix_action not in ("FIX_CODE", "ENVIRONMENT", "UNKNOWN"):
            fix_action = "UNKNOWN"

        if not isinstance(files_to_fix, list):
            files_to_fix = []

    except Exception as exc:
        print(f"Gemini analysis failed: {exc}", flush=True)

        fix_action = "UNKNOWN"
        fix_reason = f"Failed to analyze startup error: {exc}"
        files_to_fix = []

    # 4. ส่งผลวิเคราะห์ให้ Node ถัดไป
    print(f"Fix action: {fix_action}", flush=True)
    print(f"Fix reason: {fix_reason}", flush=True)
    print(f"Files to fix: {files_to_fix}", flush=True)
    print(f"Startup retry: {retry_count}/{MAX_STARTUP_RETRY}", flush=True)

    return {
        "startup_error": log_text,
        "startup_retry_count": retry_count,
        "fix_action": fix_action,
        "fix_reason": fix_reason,
        "startup_files_to_fix": files_to_fix,
        "startup_passed": False,
        "retry_after_startup": fix_action == "FIX_CODE"
        and retry_count < MAX_STARTUP_RETRY,
    }
