from langgraph import graph
from langgraph.graph import (
    StateGraph,
    END
)
from graph.state import AgentState
from nodes.find_files import find_files
from nodes.read_files import read_files
from nodes.ask_gemini import ask_gemini
from nodes.run_test import (run_test,route_test_result,analyze_test_failure)
from nodes.apply_change import apply_change
from nodes.api_discovery import api_discovery
from nodes.api_test_plan import api_test_plan
from nodes.set_postman_values import set_postman_values
from nodes.api_test import api_test
from nodes.start_application import start_application
from nodes.wait_for_application import wait_for_application
from nodes.stop_application import stop_application

def route_mode(state):

    mode = state["mode"]
    print(f"Routing mode: {mode}")
    if mode == "ALL":
        return "CODE"

    if mode == "CODE":
        return "CODE"

    if mode =="RUN_TEST":
        return "RUN_TEST"

    if mode == "API_PLAN":
        return "API_PLAN"

    if mode == "API_TEST":
        return "API_TEST"

    return "CODE"

def create_workflow():

    graph = StateGraph(
        AgentState
    )

    # -------------------------
    # Nodes
    # -------------------------

    graph.add_node("find_files", find_files )
    graph.add_node("read_files", read_files)
    graph.add_node("detect_mode",route_mode)
    graph.add_node("ask_gemini", ask_gemini)
    graph.add_node("run_test", run_test)
    graph.add_node("apply_change", apply_change)
    graph.add_node("analyze_test_failure", analyze_test_failure)
    graph.add_node("api_discovery", api_discovery)
    graph.add_node("api_test_plan", api_test_plan)
    graph.add_node("set_postman_values", set_postman_values)
    graph.add_node("start_application", start_application)
    graph.add_node("wait_for_application", wait_for_application)
    graph.add_node("api_test", api_test)
    graph.add_node("stop_application", stop_application)
    # -------------------------
    # Start
    # -------------------------

    graph.set_entry_point("find_files")

    # -------------------------
    # Flow
    # -------------------------

    graph.add_edge("find_files","read_files")
    graph.add_conditional_edges("read_files", route_mode,
        {
            "CODE": "ask_gemini",
            "RUN_TEST": "run_test",
            "API_PLAN": "start_application",
            "API_TEST": "start_application"
        }
    )

    graph.add_edge("ask_gemini","apply_change")
    graph.add_edge("apply_change","run_test")
    graph.add_edge("analyze_test_failure","ask_gemini")
    graph.add_conditional_edges("run_test",route_test_result,
        {
            "SKIP_PLAN": "start_application",
            "PASS": "api_discovery",
            "FAIL": "analyze_test_failure",
            "MAX_RETRY": END
        }
    )
    
    graph.add_edge("api_discovery", "api_test_plan")
    graph.add_edge("api_test_plan", "set_postman_values")
    graph.add_edge("set_postman_values", "start_application")
    graph.add_edge("start_application", "wait_for_application")
    graph.add_edge("wait_for_application", "api_test")
    graph.add_edge("api_test", "stop_application")
    graph.add_edge("stop_application", END)
    # -------------------------
    # Compile
    # -------------------------

    return graph.compile()