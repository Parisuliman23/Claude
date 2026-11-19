"""Loads config.yaml and .env into a typed Config."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines). Existing env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value and key not in os.environ:
            os.environ[key] = value


@dataclass
class RiskConfig:
    max_position_pct: float = 0.20
    max_total_exposure_pct: float = 0.60
    risk_per_trade_pct: float = 0.01
    max_daily_loss_pct: float = 0.02
    max_trades_per_day: int = 10
    min_order_usd: float = 10.0
    require_stop_loss: bool = True
    max_stop_distance_pct: float = 0.08
    flatten_at_utc: str | None = None


@dataclass
class Config:
    mode: str = "paper"
    exchange: str = "coinbase"
    quote_currency: str = "USD"
    symbols: list[str] = field(default_factory=lambda: ["BTC/USD", "ETH/USD"])
    paper_starting_cash: float = 10_000.0
    paper_fee_rate: float = 0.006
    paper_slippage: float = 0.0005
    decision_interval_minutes: float = 15
    monitor_interval_seconds: float = 20
    risk: RiskConfig = field(default_factory=RiskConfig)
    model: str = "claude-opus-5-5"
    effort: str = "high"
    max_tool_rounds: int = 12
    strategy_notes: str = ""
    state_dir: Path = ROOT / "state"

    @property
    def is_live(self) -> bool:
        return self.mode == "live"


def load_config(path: str | Path = ROOT / "config.yaml") -> Config:
    load_dotenv()
    raw = yaml.safe_load(Path(path).read_text()) or {}
    risk = RiskConfig(**(raw.pop("risk", None) or {}))
    cfg = Config(risk=risk, **raw)
    if cfg.mode not in ("paper", "live"):
        raise ValueError(f"mode must be 'paper' or 'live', got {cfg.mode!r}")
    cfg.state_dir = Path(cfg.state_dir)
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    return cfg
