from typing import TypedDict

class AgentState(TypedDict, total=False):

    # Mode
    mode: str

    # User request
    user_request: str

    # Java project
    project_dir: str

    # All Java files
    java_files: list[str]

    # Files selected by agent
    relevant_files: list[str]

    # Source code of relevant files
    project_context: str

    # Gemini response
    ai_response: str

    # Error
    error: str

    test_output: str
    test_passed: bool

    retry_count: int
    fix_action: str
    fix_reason: str