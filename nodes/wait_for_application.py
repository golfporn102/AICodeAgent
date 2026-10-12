
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

from config import API_BASE_URL, API_TIMEOUT
from nodes.start_application import get_application_process


def read_startup_log(log_path: Path) -> str:
    """อ่าน Log ล่าสุดสำหรับวิเคราะห์ Startup Error"""

    if log_path.exists():
        return log_path.read_text(
            encoding="utf-8",
            errors="replace",
        )[-15000:]

    return "application.log not found"


def wait_for_application(state):
    print("====== wait_for_application ======", flush=True)

    health_url = (
        f"{API_BASE_URL.rstrip('/')}/actuator/health"
    )

    project_dir = Path(state["project_dir"]).resolve()

    log_path = Path(
        state.get(
            "app_log_file",
            project_dir / "application.log",
        )
    )

    if not log_path.is_absolute():
        log_path = project_dir / log_path

    app_pid = state.get("app_pid")

    # ตรวจ Process ที่เริ่มจาก start_application
    process = (
        get_application_process(app_pid)
        if app_pid
        else None
    )

    print(f"Health URL: {health_url}", flush=True)
    print(f"Application PID: {app_pid}", flush=True)
    print(
        f"Process object available: {process is not None}",
        flush=True,
    )
    print(f"Log file: {log_path}", flush=True)

    # รอสูงสุด 120 วินาที
    deadline = time.monotonic() + 120

    last_error = "Application did not become ready"

    while time.monotonic() < deadline:

        # ---------------------------------
        # 1. ตรวจว่า Maven Process จบหรือยัง
        # ---------------------------------
        if process is not None:
            exit_code = process.poll()

            if exit_code is not None:
                log_text = read_startup_log(log_path)

                startup_error = (
                    f"Maven process exited with code {exit_code}\n"
                    f"Health URL: {health_url}\n\n"
                    f"Startup log:\n{log_text}"
                )

                print(startup_error, flush=True)

                return {
                    "app_started": False,
                    "startup_passed": False,
                    "startup_error": startup_error,
                }

        # ---------------------------------
        # 2. ตรวจ Health Check
        # ---------------------------------
        try:
            request = urllib.request.Request(
                health_url,
                headers={
                    "Accept": "application/json",
                },
                method="GET",
            )

            with urllib.request.urlopen(
                request,
                timeout=API_TIMEOUT,
            ) as response:

                body = response.read().decode(
                    "utf-8",
                    errors="replace",
                )

                try:
                    health = json.loads(body)
                except json.JSONDecodeError:
                    health = {}

                print(
                    f"Health HTTP: {response.status}",
                    flush=True,
                )
                print(
                    f"Health response: {body}",
                    flush=True,
                )

                # ต้องได้ HTTP 2xx และ status UP
                if (
                    200 <= response.status < 300
                    and health.get("status") == "UP"
                ):
                    print(
                        "Application is UP. "
                        "Routing to API test.",
                        flush=True,
                    )

                    return {
                        "app_started": True,
                        "startup_passed": True,
                        "startup_error": "",
                    }

                last_error = (
                    f"Health check not UP: {body}"
                )

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:
            last_error = str(exc)

        print(
            f"Waiting for application: {last_error}",
            flush=True,
        )

        time.sleep(2)

    # ---------------------------------
    # 3. Timeout: ส่ง Error ให้ Workflow
    # ---------------------------------
    log_text = read_startup_log(log_path)

    startup_error = (
        "Startup timeout after 120 seconds\n"
        f"Health URL: {health_url}\n"
        f"Last error: {last_error}\n\n"
        f"Startup log:\n{log_text}"
    )

    print(startup_error, flush=True)

    return {
        "app_started": False,
        "startup_passed": False,
        "startup_error": startup_error,
    }
