import json
import os
import re


def parse_ai_response(text):

    text = text.strip()

    # กรณี Gemini ส่ง ```json ... ```
    match = re.search(
        r"```json\s*(.*?)\s*```",
        text,
        re.DOTALL
    )

    if match:

        text = match.group(1).strip()

    else:

        # หา JSON object
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:

            text = text[
                start:end + 1
            ]

    return json.loads(text)


def apply_change(state):
    print("apply_change")
    project_dir = state["project_dir"]
    ai_response = state["ai_response"]

    try:

        result = parse_ai_response(
            ai_response
        )

    except Exception as e:

        print(
            "\nJSON parse error:",
            e
        )

        return {
            "error": str(e)
        }

    files = result.get(
        "files",
        []
    )

    print(
        "\nFiles to modify:",
        len(files)
    )

    for item in files:

        file_path = item["file"]
        action = item["action"]
        code = item["code"]

        if action != "modify":

            print(
                "Skip:",
                file_path
            )

            continue

        full_path = os.path.join(
            project_dir,
            file_path
        )

        # ป้องกัน path แปลก ๆ
        full_path = os.path.abspath(
            full_path
        )

        project_root = os.path.abspath(
            project_dir
        )

        if not full_path.startswith(
            project_root
        ):

            print(
                "Security warning:",
                file_path
            )

            continue

        # -------------------------
        # Backup
        # -------------------------

        backup_path = (
            full_path + ".bak"
        )

        if os.path.exists(full_path):

            with open(
                full_path,
                "r",
                encoding="utf-8"
            ) as f:

                old_code = f.read()

            with open(
                backup_path,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(old_code)

            print(
                "Backup:",
                backup_path
            )

        # -------------------------
        # Create directory
        # -------------------------

        os.makedirs(
            os.path.dirname(full_path),
            exist_ok=True
        )

        # -------------------------
        # Write new code
        # -------------------------

        with open(
            full_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(code)

        print(
            "Updated:",
            file_path
        )

    return {}