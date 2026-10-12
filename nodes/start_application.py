
import subprocess
import shutil
from pathlib import Path

# เก็บ process ไว้ให้ wait_for_application ตรวจสอบ
APP_PROCESSES = {}


def get_application_process(pid):
    return APP_PROCESSES.get(pid)


def start_application(state):
    print("====== start_application ======", flush=True)

    project_dir = Path(state["project_dir"]).resolve()
    mvnw = project_dir / "mvnw.cmd"
    mvn = shutil.which("mvn")
    log_file = project_dir / "application.log"

    if not (project_dir / "pom.xml").is_file():
        raise FileNotFoundError(f"pom.xml not found: {project_dir}")

    if mvnw.is_file():
        command = [
            "cmd.exe", "/c", str(mvnw), "spring-boot:run"
        ]
    elif mvn:
        # รองรับ Maven ที่ติดตั้งบน Windows
        command = [
            "cmd.exe", "/c", mvn, "spring-boot:run"
        ]
    else:
        raise FileNotFoundError(
            "Cannot find mvnw.cmd or Maven in PATH"
        )

    with open(log_file, "w", encoding="utf-8") as f:
        f.write("===== Starting Spring Boot =====\n")
        f.flush()

    log_handle = open(log_file, "a", encoding="utf-8")

    try:
        process = subprocess.Popen(
            command,
            cwd=str(project_dir),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    finally:
        log_handle.close()

    APP_PROCESSES[process.pid] = process

    print(f"Started PID: {process.pid}", flush=True)

    return {
        "app_pid": process.pid,
        "app_log_file": str(log_file),
        "app_started": False,
        "startup_passed": False,
        "startup_error": "",
    }
