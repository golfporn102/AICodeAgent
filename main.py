from graph.workflow import create_workflow
from config import PROJECT_DIR

def main():

    project_dir = PROJECT_DIR

    mode = input(
        "What do you want to mode [CODE, RUN_TEST]? "
    )

    user_request = input(
        "What do you want to change? "
    )

    app = create_workflow()

    result = app.invoke({
        "mode": mode,
        "user_request": user_request,
        "project_dir": project_dir

    })

    print("\n====================")
    print("Agent finished")
    print("====================")

    if result.get("error"):

        print(
            "Error:",
            result["error"]
        )


if __name__ == "__main__":

    main()