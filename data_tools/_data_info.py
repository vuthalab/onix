import json
from typing import Any, Dict


def save_data_info(info_file_path: str, info_file_content: Dict[str, Any]):
    with open(info_file_path, "w+") as f:
        json.dump(info_file_content, f)


def get_data_info(info_file_path: str):
    try:
        with open(info_file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        save_data_info(info_file_path, {})
