from pathlib import Path


def read_request_file(state: dict) -> dict:
    project_dir = Path(state.get("project_dir", ".")).resolve()

    request_file = Path(
        state.get("request_file", "request.txt")
    )

    if not request_file.is_absolute():
        request_file = project_dir / request_file

    if not request_file.exists():
        raise FileNotFoundError(
            f"Request file not found: {request_file}"
        )

    user_request = request_file.read_text(
        encoding="utf-8-sig"
    ).strip()

    if not user_request:
        raise ValueError(
            f"Request file is empty: {request_file}"
        )

    return {
        "user_request": user_request,
        "request_file": str(request_file),
    }