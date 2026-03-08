import json


def load_case(case_path: str):
    with open(case_path, "r", encoding="utf-8") as f:
        return json.load(f)