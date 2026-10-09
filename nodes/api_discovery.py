import os
import re
import json


# =========================================================
# Configuration
# =========================================================

EXCLUDED_DIRS = {
    "target",
    ".git",
    ".idea",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

HTTP_METHODS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}


# =========================================================
# Utility: Remove comments
# =========================================================

def remove_java_comments(code):
    """
    ลบ Java comments โดยพยายามรักษา string literal
    เพื่อไม่ให้ comment ในข้อความถูกลบผิดพลาด
    """

    pattern = re.compile(
        r'"(?:\\.|[^"\\])*"'
        r"|'(?:\\.|[^'\\])*'"
        r"|//[^\r\n]*"
        r"|/\*.*?\*/",
        re.S,
    )

    def replace(match):
        value = match.group(0)

        if value.startswith("//") or value.startswith("/*"):
            return re.sub(r"[^\r\n]", " ", value)

        return value

    return pattern.sub(replace, code)


# =========================================================
# Utility: Extract annotation arguments
# =========================================================

def find_annotation(code, annotation_name):
    """
    หา annotation และอ่าน arguments ภายในวงเล็บ
    รองรับวงเล็บซ้อนในระดับพื้นฐาน

    Return:
        list[str]: arguments ของ annotation แต่ละตำแหน่ง
    """

    results = []

    pattern = re.compile(
        r"@" + re.escape(annotation_name) + r"\b"
    )

    for match in pattern.finditer(code):
        index = match.end()

        while index < len(code) and code[index].isspace():
            index += 1

        if index >= len(code) or code[index] != "(":
            results.append("")
            continue

        start = index + 1
        depth = 1
        quote = None
        escaped = False

        while index + 1 < len(code) and depth > 0:
            index += 1
            char = code[index]

            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue

            if char in ('"', "'"):
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1

        if depth == 0:
            results.append(code[start:index])
        else:
            results.append("")

    return results


def extract_paths(arguments):
    """
    อ่าน path จาก annotation เช่น:
        @RequestMapping("/users")
        @RequestMapping(value = "/users")
        @RequestMapping(path = {"/users", "/members"})

    Return:
        list[str]
    """

    if not arguments:
        return [""]

    value_match = re.search(
        r"\b(?:value|path)\s*=\s*",
        arguments,
    )

    if value_match:
        value = arguments[value_match.end():]
    else:
        value = arguments

    # รองรับ array เช่น {"/users", "/members"}
    return re.findall(r'"([^"]*)"', value) or [""]


def normalize_path(path):
    """จัด path ให้เริ่มด้วย / และไม่มี / ซ้ำ"""

    path = path.strip()
    path = re.sub(r"/+", "/", path)

    if not path.startswith("/"):
        path = "/" + path

    return path or "/"


# =========================================================
# Utility: Java brace parsing
# =========================================================

def extract_braced_block(code, start):
    """
    อ่าน block { ... } โดยนับวงเล็บปีกกา
    start ต้องชี้ไปที่ opening brace
    """

    depth = 0
    quote = None
    escaped = False

    for index in range(start, len(code)):
        char = code[index]

        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                return code[start + 1:index]

    return code[start + 1:]


# =========================================================
# Find controller class
# =========================================================

def find_class_info(code):
    """
    ค้นหา class ที่มี @RestController หรือ @Controller
    """

    class_pattern = re.compile(
        r"@\s*(?:RestController|Controller)\b"
    )

    for annotation_match in class_pattern.finditer(code):
        class_match = re.search(
            r"\bclass\s+(\w+)",
            code[annotation_match.end():],
        )

        if not class_match:
            continue

        class_name = class_match.group(1)
        absolute_start = (
            annotation_match.end() + class_match.start()
        )

        brace_start = code.find("{", absolute_start)

        if brace_start == -1:
            continue

        class_body = extract_braced_block(code, brace_start)

        # หาค่า @RequestMapping ก่อน class declaration
        prefix = code[:absolute_start]

        mappings = find_annotation(
            prefix,
            "RequestMapping",
        )

        base_paths = (
            extract_paths(mappings[-1])
            if mappings
            else [""]
        )

        return {
            "class": class_name,
            "class_start": absolute_start,
            "body_start": brace_start,
            "body": class_body,
            "base_paths": base_paths,
        }

    return None


# =========================================================
# Find DTO type
# =========================================================

def find_request_body_type(parameters):
    """
    หา type ของ parameter ที่มี @RequestBody

    ตัวอย่าง:
        @RequestBody CreateUserRequest request
        @RequestBody final CreateUserRequest request
        @RequestBody List<CreateUserRequest> requests
    """

    body_annotation = re.search(
        r"@\s*RequestBody\b",
        parameters,
    )

    if not body_annotation:
        return None

    tail = parameters[body_annotation.end():]

    type_match = re.search(
        r"\s*(?:final\s+)?"
        r"([\w.$]+(?:\s*<[^>]+>)?(?:\[\])?)"
        r"\s+\w+",
        tail,
    )

    if not type_match:
        return None

    type_name = type_match.group(1).strip()

    # List<CreateUserRequest> -> CreateUserRequest
    generic_match = re.search(
        r"<\s*([\w.$]+)",
        type_name,
    )

    if generic_match:
        return generic_match.group(1).split(".")[-1]

    return type_name.replace("[]", "").split(".")[-1]


# =========================================================
# Java type -> JSON example
# =========================================================

def sample_value(java_type):
    """
    สร้างค่า JSON ตัวอย่างจาก Java type
    """

    java_type = java_type.strip()
    simple_type = java_type.split(".")[-1]

    if simple_type in {
        "String",
        "CharSequence",
        "UUID",
    }:
        return "string"

    if simple_type in {
        "int",
        "Integer",
        "long",
        "Long",
        "short",
        "Short",
        "byte",
        "Byte",
    }:
        return 0

    if simple_type in {
        "double",
        "Double",
        "float",
        "Float",
        "BigDecimal",
    }:
        return 0.0

    if simple_type in {"boolean", "Boolean"}:
        return True

    if simple_type == "LocalDate":
        return "2026-01-01"

    if simple_type in {
        "LocalDateTime",
        "OffsetDateTime",
    }:
        return "2026-01-01T10:00:00"

    if simple_type == "Date":
        return "2026-01-01T10:00:00Z"

    if simple_type.startswith(("List<", "Set<")):
        return []

    if simple_type.startswith("Map<"):
        return {}

    if simple_type.endswith("[]"):
        return []

    # enum หรือ custom object
    return "string"


# =========================================================
# Parse DTO fields
# =========================================================

def parse_java_fields(parameters):
    """
    อ่าน fields จาก Java record parameters
    """

    fields = {}

    for part in parameters.split(","):
        part = part.strip()

        match = re.search(
            r"([\w.$<>?, \[\]]+?)\s+(\w+)\s*$",
            part,
        )

        if match:
            field_type = match.group(1).strip()
            field_name = match.group(2)

            fields[field_name] = sample_value(field_type)

    return fields


def find_dto_fields(project_dir, dto_type, visited=None):
    """
    ค้นหา DTO class หรือ record แล้วสร้าง JSON ตัวอย่าง

    รองรับ:
        private String name;
        private Integer age;
        public record CreateUserRequest(String name, Integer age)

    Nested DTO จะพยายามค้นหาเพิ่มเติม
    """

    if not dto_type:
        return {}

    if visited is None:
        visited = set()

    dto_type = dto_type.split(".")[-1]

    if dto_type in visited:
        return {}

    visited.add(dto_type)

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in EXCLUDED_DIRS
        ]

        for filename in files:
            if not filename.endswith(".java"):
                continue

            file_path = os.path.join(root, filename)

            try:
                with open(
                    file_path,
                    "r",
                    encoding="utf-8-sig",
                ) as file:
                    raw_code = file.read()
            except (OSError, UnicodeError):
                continue

            code = remove_java_comments(raw_code)

            # Java record
            record_match = re.search(
                r"\brecord\s+"
                + re.escape(dto_type)
                + r"\s*\((.*?)\)",
                code,
                re.S,
            )

            if record_match:
                fields = parse_java_fields(
                    record_match.group(1)
                )

                return expand_nested_fields(
                    project_dir,
                    fields,
                    visited,
                )

            # Java class
            class_match = re.search(
                r"\bclass\s+"
                + re.escape(dto_type)
                + r"\b",
                code,
            )

            if not class_match:
                continue

            brace_start = code.find(
                "{",
                class_match.end(),
            )

            if brace_start == -1:
                continue

            class_body = extract_braced_block(
                code,
                brace_start,
            )

            fields = {}

            field_pattern = re.compile(
                r"^\s*(?:private|protected|public)\s+"
                r"(?:static\s+)?(?:final\s+)?"
                r"([\w.$<>?, \[\]]+?)\s+"
                r"(\w+)\s*(?:=[^;]*)?;",
                re.M,
            )

            for match in field_pattern.finditer(class_body):
                declaration = match.group(0)
                field_type = match.group(1).strip()
                field_name = match.group(2)

                if re.search(r"\bstatic\b", declaration):
                    continue

                fields[field_name] = sample_value(field_type)

            return expand_nested_fields(
                project_dir,
                fields,
                visited,
            )

    print(f"DTO not found: {dto_type}")

    return {}


def expand_nested_fields(project_dir, fields, visited):
    """
    พยายามเติม field ของ nested DTO
    เช่น CreateUserRequest.address -> AddressRequest
    """

    result = dict(fields)

    for field_name, value in fields.items():
        if value != "string":
            continue

        # ถ้า field เป็น custom object จะต้องตรวจ type
        # จาก declaration เพิ่มเติม จึงไม่เดา type จากชื่อ field
        # เพื่อป้องกันการสร้าง schema ผิด
        #
        # สามารถขยายส่วนนี้ภายหลังเพื่อรองรับ nested DTO
        pass

    return result


# =========================================================
# Find controller APIs
# =========================================================

def discover_controller_apis(project_dir, java_file, code):
    """
    ค้นหา API mappings ใน Controller
    """

    class_info = find_class_info(code)

    if not class_info:
        return None

    class_name = class_info["class"]
    class_body = class_info["body"]
    base_paths = class_info["base_paths"]

    apis = []

    mapping_names = [
        "GetMapping",
        "PostMapping",
        "PutMapping",
        "DeleteMapping",
        "PatchMapping",
        "RequestMapping",
    ]

    # หา annotation ใน class body
    annotations = []

    for annotation_name in mapping_names:
        for arguments in find_annotation(
            class_body,
            annotation_name,
        ):
            annotations.append({
                "annotation": annotation_name,
                "arguments": arguments,
            })

    # ค้นหาแต่ละ mapping โดยใช้ตำแหน่ง annotation
    annotation_pattern = re.compile(
        r"@\s*(GetMapping|PostMapping|PutMapping|"
        r"DeleteMapping|PatchMapping|RequestMapping)\b"
    )

    for match in annotation_pattern.finditer(class_body):
        annotation = match.group(1)

        # อ่าน arguments โดยหา annotation ที่ตำแหน่งนี้
        tail = class_body[match.start():]

        argument_match = re.match(
            r"@\s*\w+\s*(?:\(([^)]*)\))?",
            tail,
        )

        arguments = (
            argument_match.group(1) or ""
            if argument_match
            else ""
        )

        if annotation == "RequestMapping":
            method_match = re.search(
                r"\bmethod\s*=\s*"
                r"\{?\s*RequestMethod\.(GET|POST|PUT|DELETE|PATCH)",
                arguments,
            )

            if not method_match:
                continue

            http_method = method_match.group(1)
        else:
            http_method = HTTP_METHODS[annotation]

        paths = extract_paths(arguments)

        # ค้นหา method signature หลัง annotation
        after_annotation = class_body[match.end():]

        method_match = re.search(
            r"\s*(?:@\w+(?:\([^)]*\))?\s*)*"
            r"(?:public|protected|private)?\s*"
            r"[\w.$<>?, \[\]]+\s+"
            r"(\w+)\s*\((.*?)\)\s*"
            r"(?:throws\s+[\w., ]+\s*)?\{",
            after_annotation,
            re.S,
        )

        if not method_match:
            continue

        method_name = method_match.group(1)
        parameters = method_match.group(2)

        request_body_type = find_request_body_type(
            parameters
        )

        request_body = (
            find_dto_fields(project_dir, request_body_type)
            if request_body_type
            else {}
        )

        for base_path in base_paths:
            for path in paths:
                endpoint = normalize_path(
                    base_path.rstrip("/") + "/" + path.lstrip("/")
                )

                apis.append({
                    "method": http_method,
                    "path": endpoint,
                    "method_name": method_name,
                    "request_body_type": request_body_type,
                    "request_body": request_body,
                })

    if not apis:
        return None

    return {
        "file": os.path.relpath(java_file, project_dir),
        "class": class_name,
        "base_path": base_paths,
        "apis": apis,
    }


# =========================================================
# Save Postman collection
# =========================================================

def save_postman_collection(project_dir, controllers):
    """
    สร้าง Postman Collection v2.1
    """

    collection = {
        "info": {
            "name": "AI Agent API Tests",
            "_postman_id": "ai-agent-api-tests",
            "schema": (
                "https://schema.getpostman.com/json/"
                "collection/v2.1.0/collection.json"
            ),
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://localhost:8080",
            }
        ],
        "item": [],
    }

    for controller in controllers:
        controller_item = {
            "name": controller["class"],
            "item": [],
        }

        for api in controller["apis"]:
            method = api["method"]
            path = api["path"]

            # Spring {id} -> Postman :id
            postman_path = re.sub(
                r"\{([^}]+)\}",
                r":\1",
                path,
            )

            path_parts = [
                part
                for part in postman_path.split("/")
                if part
            ]

            request = {
                "method": method,
                "header": [],
                "url": {
                    "raw": "{{baseUrl}}" + postman_path,
                    "host": ["{{baseUrl}}"],
                    "path": path_parts,
                },
            }

            if method in ("POST", "PUT", "PATCH"):
                request["header"].append({
                    "key": "Content-Type",
                    "value": "application/json",
                })

                body = api.get("request_body", {})

                request["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(
                        body,
                        indent=2,
                        ensure_ascii=False,
                    ),
                    "options": {
                        "raw": {
                            "language": "json",
                        }
                    },
                }

            controller_item["item"].append({
                "name": f"{method} {path}",
                "request": request,
            })

        collection["item"].append(controller_item)

    output_file = os.path.join(
        project_dir,
        "postman_collection.json",
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            collection,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Postman collection saved: {output_file}")

    return output_file


# =========================================================
# LangGraph node
# =========================================================

def api_discovery(state):
    """
    LangGraph node:
        1. ค้นหา Controller
        2. ค้นหา API
        3. ค้นหา Request DTO
        4. สร้าง Postman Collection
    """

    project_dir = state["project_dir"]
    controllers = []

    if not os.path.isdir(project_dir):
        raise FileNotFoundError(
            f"Project directory not found: {project_dir}"
        )

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in EXCLUDED_DIRS
        ]

        for filename in files:
            if not filename.endswith(".java"):
                continue

            java_file = os.path.join(root, filename)

            try:
                with open(
                    java_file,
                    "r",
                    encoding="utf-8-sig",
                ) as file:
                    raw_code = file.read()
            except (OSError, UnicodeError) as error:
                print(f"Skip {java_file}: {error}")
                continue

            code = remove_java_comments(raw_code)

            controller = discover_controller_apis(
                project_dir,
                java_file,
                code,
            )

            if controller:
                controllers.append(controller)

    print("\n========== API DISCOVERY ==========")

    for controller in controllers:
        print(f"\nController: {controller['class']}")
        print(f"File: {controller['file']}")

        for api in controller["apis"]:
            print(
                f"  {api['method']:6} "
                f"{api['path']:35} "
                f"{api['method_name']}"
            )

            if api["request_body_type"]:
                print(
                    "    Request DTO: "
                    f"{api['request_body_type']}"
                )

                print(
                    "    Request Body: "
                    + json.dumps(
                        api["request_body"],
                        ensure_ascii=False,
                    )
                )

    print("\n===================================")

    postman_file = save_postman_collection(
        project_dir,
        controllers,
    )

    print(f"api_endpoints: {controllers}")
    return {
        "api_endpoints": controllers,
        "postman_file": postman_file,
    }
