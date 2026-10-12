
from langgraph.graph import StateGraph, END

from graph.state import AgentState

from nodes.find_files import find_files
from nodes.read_files import read_files
from nodes.read_request_file import read_request_file
from nodes.ask_gemini import ask_gemini
from nodes.run_test import (
    run_test,
    route_test_result,
    analyze_test_failure,
)
from nodes.apply_change import apply_change
from nodes.api_discovery import api_discovery
from nodes.api_test_plan import api_test_plan
from nodes.set_postman_values import set_postman_values
from nodes.api_test import api_test
from nodes.start_application import start_application
from nodes.wait_for_application import wait_for_application
from nodes.stop_application import stop_application
from nodes.analyze_startup_failure import analyze_startup_failure

from config import MAX_STARTUP_RETRY


# -------------------------
# Routing functions
# -------------------------

def route_mode(state):
    mode = state.get("mode", "CODE")

    print(f"Routing mode: {mode}", flush=True)

    if mode in ("ALL", "CODE"):
        return "CODE"

    if mode == "RUN_TEST":
        return "RUN_TEST"

    if mode == "API_PLAN":
        return "API_PLAN"

    if mode == "API_TEST":
        return "API_TEST"

    return "CODE"


def route_application_start(state):
    print(
        f"Routing application: app_started={state.get('app_started')}",
        flush=True,
    )

    if state.get("app_started") is True:
        return "API_TEST"

    return "STOP_FOR_ANALYSIS"


def route_after_stop(state):
    """แยกการ Stop ปกติกับการ Stop เพราะ Startup Error"""

    if not state.get("app_started", False):
        return "ANALYZE_STARTUP_FAILURE"

    return "END"


def route_startup_analysis(state):
    """ตัดสินใจว่าจะให้ AI แก้ Code หรือหยุด"""

    action = state.get("fix_action", "UNKNOWN")
    retry_count = state.get("startup_retry_count", 0)

    if action == "FIX_CODE" and retry_count < MAX_STARTUP_RETRY:
        return "FIX_CODE"

    return "STOP"


def route_after_test(state):
    """หลังแก้ Startup Error แล้ว ต้อง Start แอปใหม่ ไม่ใช่ API discovery"""

    if state.get("startup_repair_mode", False):
        if state.get("test_passed", False):
            return "RESTART_APP"

        # ใช้ routing เดิมสำหรับ Unit Test ที่ไม่ผ่าน
        return route_test_result(state)

    return route_test_result(state)


# -------------------------
# Create workflow
# -------------------------

def create_workflow():

    workflow = StateGraph(AgentState)

    # -------------------------
    # Nodes
    # -------------------------

    workflow.add_node("find_files", find_files)
    workflow.add_node("read_files", read_files)
    workflow.add_node("read_request_file", read_request_file)
    workflow.add_node("ask_gemini", ask_gemini)
    workflow.add_node("run_test", run_test)
    workflow.add_node("apply_change", apply_change)
    workflow.add_node("analyze_test_failure", analyze_test_failure)

    workflow.add_node("api_discovery", api_discovery)
    workflow.add_node("api_test_plan", api_test_plan)
    workflow.add_node("set_postman_values", set_postman_values)
    workflow.add_node("api_test", api_test)

    workflow.add_node("start_application", start_application)
    workflow.add_node("wait_for_application", wait_for_application)
    workflow.add_node("stop_application", stop_application)
    workflow.add_node("analyze_startup_failure", analyze_startup_failure)

    # -------------------------
    # Entry point
    # -------------------------

    workflow.set_entry_point("read_request_file")

    # -------------------------
    # Read project
    # -------------------------

    workflow.add_edge("read_request_file", "find_files")
    workflow.add_edge("find_files", "read_files")

    workflow.add_conditional_edges(
        "read_files",
        route_mode,
        {
            "CODE": "ask_gemini",
            "RUN_TEST": "run_test",
            "API_PLAN": "start_application",
            "API_TEST": "start_application",
        },
    )

    # -------------------------
    # Code generation and tests
    # -------------------------

    workflow.add_edge("ask_gemini", "apply_change")
    workflow.add_edge("apply_change", "run_test")

    workflow.add_edge(
        "analyze_test_failure",
        "ask_gemini"
    )

    workflow.add_conditional_edges(
        "run_test",
        route_after_test,
        {
            "SKIP_PLAN": "start_application",
            "PASS": "api_discovery",
            "FAIL": "analyze_test_failure",
            "MAX_RETRY": END,
            "RESTART_APP": "start_application",
        },
    )

    # -------------------------
    # API testing
    # -------------------------

    workflow.add_edge("api_discovery", "api_test_plan")
    workflow.add_edge("api_test_plan", "set_postman_values")
    workflow.add_edge("set_postman_values", "start_application")

    # -------------------------
    # Application startup
    # -------------------------

    workflow.add_edge(
        "start_application",
        "wait_for_application"
    )

    workflow.add_conditional_edges(
        "wait_for_application",
        route_application_start,
        {
            "API_TEST": "api_test",
            "STOP_FOR_ANALYSIS": "stop_application",
        },
    )

    # -------------------------
    # Stop application
    # -------------------------

    workflow.add_conditional_edges(
        "stop_application",
        route_after_stop,
        {
            "ANALYZE_STARTUP_FAILURE": "analyze_startup_failure",
            "END": END,
        },
    )

    # -------------------------
    # Analyze startup failure
    # -------------------------

    workflow.add_conditional_edges(
        "analyze_startup_failure",
        route_startup_analysis,
        {
            "FIX_CODE": "ask_gemini",
            "STOP": END,
        },
    )

    # -------------------------
    # API test cleanup
    # -------------------------

    workflow.add_edge("api_test", "stop_application")

    # -------------------------
    # Compile
    # -------------------------

    return workflow.compile()
