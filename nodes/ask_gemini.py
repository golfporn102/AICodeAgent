import json
from google import genai
from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL
)


client = genai.Client(
    api_key=GEMINI_API_KEY
)


def ask_gemini(state):
    print("ask_gemini")
    user_request = state["user_request"]
    project_context = state["project_context"]
    test_output = state.get("test_output", "")
    fix_action = state.get("fix_action", "")
    fix_reason = state.get("fix_reason", "")

    prompt = f"""
You are a Java Spring Boot coding agent.

User request:

{user_request}

Relevant Java files:

{project_context}

Test result:

{test_output if test_output else "No test has been run yet. This is the initial coding request."}

Test failure analysis:

Fix action:
{fix_action if fix_action else "N/A - This is the initial coding request."}

Reason:
{fix_reason if fix_reason else "N/A - There is no previous test failure."}

Your task:

1. Analyze the user request.
2. Analyze the test result and test failure analysis.
3. Identify ALL files that actually need modification.
4. Modify ONLY the necessary files.
5. If the fix action is FIX_CODE, modify production code under src/main.
6. If the fix action is FIX_TEST, modify only Unit Test files under src/test.
7. Do NOT modify files that are unrelated to the problem.
8. Do NOT return unchanged files.
9. Return the COMPLETE source code for each modified file.
10. Do NOT create unnecessary files.
11. Preserve the existing package structure, imports, class names, method signatures, and project conventions unless the requested fix requires changing them.
12. Do not remove existing functionality that is unrelated to the requested fix.

IMPORTANT:

Return ONLY valid JSON.

Do NOT use markdown.
Do NOT use ```json.
Do NOT add explanation outside the JSON.

JSON escaping rules:

- Escape every double quote inside Java source code as \\".
- Escape every backslash inside Java source code as \\\\.
- Use \\n for newline characters.
- Use \\t for tab characters when necessary.
- Never output invalid JSON escape sequences such as \d, \s, \w, \., or \(
- For Java regular expressions, remember that JSON escaping and Java escaping are both required.

For example, Java code:

String regex = "\\\\d+";

must be represented correctly inside the JSON string.

Return this exact JSON structure:

{{
  "files": [
    {{
      "file": "src/main/java/example/UserController.java",
      "action": "modify",
      "code": "complete source code"
    }}
  ]
}}

If no file needs modification, return:

{{
  "files": []
}}
"""

    print("\nCalling Gemini...")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    ai_response = response.text

    print("\nGemini response:")
    print(ai_response)

    return {
        "ai_response": ai_response
    }