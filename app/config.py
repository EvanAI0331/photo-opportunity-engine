from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class AgentSettings:
    api_key: str
    base_url: str
    model: str
    thinking_type: str
    max_completion_tokens: int
    temperature: float


@dataclass(frozen=True)
class FlickrSettings:
    api_key: str


def get_agent_settings() -> AgentSettings:
    load_dotenv()
    return AgentSettings(
        api_key=os.getenv("MINIMAX_API_KEY", ""),
        base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1").rstrip("/"),
        model=os.getenv("MINIMAX_MODEL", "MiniMax-M3"),
        thinking_type=os.getenv("MINIMAX_THINKING_TYPE", "disabled"),
        max_completion_tokens=int(os.getenv("MINIMAX_MAX_COMPLETION_TOKENS", "1200")),
        temperature=float(os.getenv("MINIMAX_TEMPERATURE", "0.2")),
    )


def get_flickr_settings() -> FlickrSettings:
    load_dotenv()
    return FlickrSettings(api_key=os.getenv("FLICKR_API_KEY", ""))
