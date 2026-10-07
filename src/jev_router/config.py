import json
import os
from pathlib import Path


def config_home():
    override = os.environ.get("JEV_ROUTER_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".config" / "jev"


def load_settings(folder):
    """只讀兩個設定，不載入或輸出其他服務的金鑰。"""
    values = {}
    path = folder / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.strip().removeprefix("export ").partition("=")
            if separator and name.strip() in {"TYPESAFE_API_KEY", "TYPESAFE_MODEL"}:
                value = value.strip()
                if value.startswith(("\"", "'")) and value[-1:] == value[:1]:
                    value = value[1:-1]
                else:
                    value = value.split(" #", 1)[0].rstrip()
                values[name.strip()] = value
    for name in ("TYPESAFE_API_KEY", "TYPESAFE_MODEL"):
        if name in os.environ:
            values[name] = os.environ[name]
    if not values.get("TYPESAFE_API_KEY", "").strip():
        raise ValueError("缺少 TYPESAFE_API_KEY；請設定共用 .env。")
    values.setdefault("TYPESAFE_MODEL", "jev-latest")
    if not values["TYPESAFE_MODEL"].strip():
        raise ValueError("TYPESAFE_MODEL 不可留白。")
    return values


def load_candidates(folder, client):
    profiles = json.loads((folder / "models.json").read_text(encoding="utf-8-sig"))
    candidates = profiles.get(client) if isinstance(profiles, dict) else None
    if not isinstance(candidates, dict) or not candidates:
        raise ValueError("此 client 沒有模型清單；請設定 models.json。")
    for route, item in candidates.items():
        if not isinstance(route, str) or not route.strip() or not isinstance(item, dict):
            raise ValueError("模型清單格式錯誤。")
        for field in ("model", "description"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError("每個候選模型需要 model 和 description。")
    return candidates
