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
    # --- Ross Cameron discipline rules ---
    max_consecutive_losses: int = 3          # 3 losers in a row = done for the day
    giveback_pct_of_peak: float = 0.5        # stop after giving back 50% of the day's peak profit
    giveback_min_peak_pct: float = 0.005     # ...once the peak was at least 0.5% of equity
    starter_size_fraction: float = 0.25      # trade 1/4 size until the day has a cushion
    cushion_pct: float = 0.005               # crypto cushion: day P&L >= 0.5% of equity
    cushion_per_share: float = 0.20          # stocks (Ross): 1/4 size "until I have made 20 cents per share"
    scale_out_fraction: float = 0.5          # sell half at the first target...
    move_stop_to_breakeven: bool = True      # ...and move the stop to break-even
    # "Breakout or bailout" (Ross): price should move up at least 10 cents within ~1 minute.
    breakout_or_bailout_minutes: float | None = 1.5
    bailout_min_move: float = 0.10           # stocks: $/share (crypto uses 0.3% of price)
    # "The exit indicator is the first candle that makes a new low."
    exit_on_new_low_candle: bool = True
    exit_candle_timeframe: str = "1m"
    trade_window: str | None = None          # "07:00-11:00" (in trade_window_tz); null = always
    trade_window_tz: str = "America/New_York"


@dataclass
class ScannerConfig:
    universe_size: int = 50          # top gainers pulled from the market each scan
    max_candidates: int = 10
    # stocks (Ross's 5 pillars)
    price_min: float = 1.0
    price_max: float = 20.0
    min_gain_pct: float = 10.0
    min_rvol: float = 5.0
    max_float: float = 20_000_000
    require_news: bool = False       # Ross: catalyst "preferred"; no-news movers = trade with caution
    no_news_size_factor: float = 0.5 # ...so they get half size
    thin_volume_shares: float = 500_000      # below this day volume = thin liquidity
    thin_volume_size_factor: float = 0.5     # Ross: "I mitigate the risk by reducing my share size"
    max_pct_of_day_volume: float = 0.02      # never buy more than 2% of the day's volume
    cold_market_max_float: float = 10_000_000  # Ross: float cutoff drops to 10M when the market is cold
    require_float_known: bool = False
    news_max_age_hours: float = 24
    # crypto adaptation
    crypto_min_rvol: float = 3.0
    crypto_min_quote_volume: float = 1_000_000


@dataclass
class Config:
    mode: str = "paper"
    market: str = "crypto"            # crypto | stocks
    decision_mode: str = "rules"      # rules (no Claude, free) | claude (needs ANTHROPIC_API_KEY)
    stocks_data_feed: str = "iex"     # iex (free) | sip (paid Alpaca data plan)
    iex_volume_share: float = 0.03    # IEX prints ~3% of US volume; used to estimate real volume
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    watch_interval_seconds: float = 15  # how often code checks watchlist charts for setups
    setup_timeframe: str = "1m"
    alert_effort: str = "medium"        # Claude effort when woken by a live setup (faster)
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
    scanner = ScannerConfig(**(raw.pop("scanner", None) or {}))
    cfg = Config(risk=risk, scanner=scanner, **raw)
    cfg.symbols = cfg.symbols or []
    if cfg.mode not in ("paper", "live"):
        raise ValueError(f"mode must be 'paper' or 'live', got {cfg.mode!r}")
    if cfg.decision_mode not in ("rules", "claude"):
        raise ValueError(f"decision_mode must be 'rules' or 'claude', got {cfg.decision_mode!r}")
    if cfg.market not in ("crypto", "stocks"):
        raise ValueError(f"market must be 'crypto' or 'stocks', got {cfg.market!r}")
    cfg.state_dir = Path(cfg.state_dir)
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    return cfg
