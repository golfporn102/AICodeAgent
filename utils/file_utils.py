import os


def find_java_files(project_dir):

    java_files = []

    for root, dirs, files in os.walk(project_dir):

        # ไม่ค้น folder เหล่านี้
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

    return java_files


def read_file(project_dir, file_path):

    full_path = os.path.join(
        project_dir,
        file_path
    )

    with open(
        full_path,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()