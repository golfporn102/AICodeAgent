
import subprocess


def stop_application(state):
    print(f"====== stop_application ==================")
    pid = state.get("app_pid")

    # ไม่ปิด Process ถ้า Agent ไม่ได้เป็นผู้ Start
    if not pid:
        return {
            "app_stopped": False,
            "stop_message": "No application PID; nothing to stop."
        }

    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        return {
            "app_stopped": True,
            "stop_message": f"Stopped application process PID={pid}"
        }

    except subprocess.CalledProcessError as exc:
        return {
            "app_stopped": False,
            "stop_message": (
                f"Unable to stop PID={pid}: {exc.stderr}"
            )
        }

    except subprocess.TimeoutExpired:
        return {
            "app_stopped": False,
            "stop_message": f"Timeout stopping PID={pid}"
        }