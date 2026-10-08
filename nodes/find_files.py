import os


def find_files(state):
    print("find_files")
    project_dir = state["project_dir"]
    user_request = state["user_request"].lower()

    java_files = []

    for root, dirs, files in os.walk(project_dir):

        dirs[:] = [
            d for d in dirs
            if d not in [
                "target",
                ".git",
                ".idea"
            ]
        ]

        for file in files:

            if file.endswith(".java"):

                full_path = os.path.join(
                    root,
                    file
                )

                relative_path = os.path.relpath(
                    full_path,
                    project_dir
                )

                java_files.append(relative_path)

    # -------------------------
    # หาไฟล์ที่เกี่ยวข้อง
    # -------------------------

    relevant_files = []

    # keyword จาก request
    keywords = []

    possible_words = [
        "user",
        "order",
        "product",
        "customer",
        "payment",
        "account"
    ]

    for word in possible_words:

        if word in user_request:
            keywords.append(word)

    for file in java_files:

        filename = os.path.basename(file).lower()

        for keyword in keywords:

            if keyword in filename:

                if file not in relevant_files:
                    relevant_files.append(file)

    # -------------------------
    # ถ้าหาไม่เจอ
    # -------------------------

    if not relevant_files:

        # เอา Controller ก่อน
        for file in java_files:

            if "controller" in file.lower():

                relevant_files.append(file)

    print("\nJava files:", len(java_files))

    print("\nRelevant files:")

    for file in relevant_files:
        print(" -", file)

    return {
        "java_files": java_files,
        "relevant_files": relevant_files
    }