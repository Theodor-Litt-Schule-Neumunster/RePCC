import os
from typing import Any, Dict, List, Tuple

import yaml

from constants import DEFAULT_SETTINGS_DIR, ROAMING_DATA_DIR, ROAMING_SETTINGS_DIR


SETTING_FILES = ["debug.yaml", "presentationTools.yaml", "webrtc.yaml"]


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml_if_exists(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if isinstance(data, dict):
        return data
    return {}


def load_settings() -> Dict[str, Dict[str, Any]]:
    settings: Dict[str, Dict[str, Any]] = {}

    for file_name in SETTING_FILES:
        structure_path = os.path.join(DEFAULT_SETTINGS_DIR, file_name)
        roaming_path = os.path.join(ROAMING_SETTINGS_DIR, file_name)

        defaults = _load_yaml_if_exists(structure_path)
        current = _load_yaml_if_exists(roaming_path)

        merged = _deep_merge(defaults, current)
        settings[file_name] = merged

    return settings


def save_settings(settings: Dict[str, Dict[str, Any]]) -> None:
    os.makedirs(ROAMING_SETTINGS_DIR, exist_ok=True)

    for file_name in SETTING_FILES:
        file_data = settings.get(file_name, {})
        file_path = os.path.join(ROAMING_SETTINGS_DIR, file_name)
        with open(file_path, "w", encoding="utf-8") as stream:
            yaml.safe_dump(file_data, stream, sort_keys=False)


def load_register() -> Dict[str, Any]:
    register_path = os.path.join(ROAMING_DATA_DIR, "register.yaml")
    return _load_yaml_if_exists(register_path)


def parse_devices(register_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    connected_now: List[str] = []
    known_or_old: List[str] = []

    ip_data = register_data.get("IP")
    if isinstance(ip_data, dict):
        for _, value in ip_data.items():
            if value:
                connected_now.append(str(value))
    elif isinstance(ip_data, list):
        for value in ip_data:
            if value:
                connected_now.append(str(value))
    elif ip_data:
        connected_now.append(str(ip_data))

    mac_data = register_data.get("MAC")
    if isinstance(mac_data, list):
        known_or_old.extend([str(item) for item in mac_data if item])
    elif isinstance(mac_data, dict):
        known_or_old.extend([str(v) for v in mac_data.values() if v])
    elif mac_data:
        known_or_old.append(str(mac_data))

    return connected_now, known_or_old
