
import subprocess
from pathlib import Path


def start_application(state):
    print("====== start_application ======", flush=True)

    project_dir = Path(state["project_dir"]).resolve()
    mvnw = project_dir / "mvnw.cmd"
    log_file = project_dir / "application.log"

    print(f"Project: {project_dir}", flush=True)
    print(f"Maven: {mvnw}", flush=True)
    print(f"Log: {log_file}", flush=True)

    if not mvnw.exists():
        raise FileNotFoundError(f"ไม่พบ Maven Wrapper: {mvnw}")

    # สร้าง log และเขียนข้อความทันที
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("\n===== Starting Spring Boot =====\n")
        f.flush()

    with open(log_file, "a", encoding="utf-8") as f:
        process = subprocess.Popen(
            ["cmd.exe", "/c", str(mvnw), "spring-boot:run"],
            cwd=str(project_dir),
            stdout=f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    print(f"Started PID: {process.pid}", flush=True)

    return {
        "app_pid": process.pid,
        "app_log_file": str(log_file),
        "app_started": False,
    }