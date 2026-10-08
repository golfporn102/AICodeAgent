from utils.file_utils import read_file


def read_files(state):
    print("read_files")
    project_dir = state["project_dir"]
    relevant_files = state["relevant_files"]

    context = ""

    for file in relevant_files:

        try:

            code = read_file(
                project_dir,
                file
            )

            context += f"""
========================================
FILE: {file}
========================================

{code}

"""

        except Exception as e:

            print(
                f"Cannot read {file}: {e}"
            )

    print(
        "\nContext files:",
        len(relevant_files)
    )

    return {
        "project_context": context
    }