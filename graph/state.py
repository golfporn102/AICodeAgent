from typing import TypedDict, Any

class AgentState(TypedDict, total=False):

    # Mode
    mode: str

    #Mode test
    mode_test: str

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

    api_endpoints: list[dict[str, Any]]
    postman_file: str
    test_plan: list[dict[str, Any]]
    test_plan_file: str

    app_pid: int
    app_log_file: str
    app_started: bool

    api_test_results: list[dict[str, Any]]
    api_test_passed: bool
    api_test_output: str
    api_test_results_file: str