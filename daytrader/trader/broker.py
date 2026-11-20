"""Brokers: PaperBroker simulates fills at live prices; LiveBroker sends real orders via ccxt.

Both are long-only spot (you buy a coin, later sell it). Stop-loss and take-profit
levels are tracked locally and enforced by the monitor loop in code, so they work
the same on every exchange.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .market import MarketData


@dataclass
class Position:
    symbol: str
    qty: float
    entry_price: float
    stop_loss: float | None
    take_profit: float | None
    opened_at: float
    cost_usd: float  # cost basis of the shares still held, incl. fees
    initial_stop: float | None = None
    scaled_out: bool = False      # half already sold at the first target
    realized_usd: float = 0.0     # P&L already banked from partial sells
    initial_qty: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Fill:
    symbol: str
    side: str
    qty: float
    price: float
    fee_usd: float
    value_usd: float
    ts: float
    order_id: str | None = None


class BaseBroker:
    def __init__(self, market: MarketData, state_path: Path):
        self.market = market
        self.state_path = state_path
        self.positions: dict[str, Position] = {}
        self.realized: list[dict] = []  # closed-trade records

    # -- persistence -------------------------------------------------------
    def _extra_state(self) -> dict:
        return {}

    def _load_extra(self, data: dict) -> None:
        pass

    def save(self) -> None:
        data = {
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "realized": self.realized[-500:],
            **self._extra_state(),
        }
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.state_path)

    def load(self) -> None:
        if not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text())
        self.positions = {s: Position(**p) for s, p in data.get("positions", {}).items()}
        self.realized = data.get("realized", [])
        self._load_extra(data)

    # -- account -----------------------------------------------------------
    def cash(self) -> float:
        raise NotImplementedError

    def position_value(self, symbol: str) -> float:
        p = self.positions.get(symbol)
        return p.qty * self.market.price(symbol) if p else 0.0

    def exposure(self) -> float:
        return sum(self.position_value(s) for s in self.positions)

    def equity(self) -> float:
        return self.cash() + self.exposure()

    # -- orders --------------------------------------------------------------
    def _buy(self, symbol: str, usd: float) -> Fill:
        raise NotImplementedError

    def _sell(self, symbol: str, qty: float) -> Fill:
        raise NotImplementedError

    def open_long(self, symbol: str, usd: float, stop: float | None, tp: float | None) -> Fill:
        if symbol in self.positions:
            raise ValueError(f"Already holding {symbol}")
        fill = self._buy(symbol, usd)
        self.positions[symbol] = Position(
            symbol=symbol,
            qty=fill.qty,
            entry_price=fill.price,
            stop_loss=stop,
            take_profit=tp,
            opened_at=fill.ts,
            cost_usd=fill.value_usd + fill.fee_usd,
            initial_stop=stop,
            initial_qty=fill.qty,
        )
        self.save()
        return fill

    def reduce(self, symbol: str, fraction: float, reason: str) -> dict:
        """Sell part (or all, fraction=1) of a position. Returns a trade record."""
        pos = self.positions.get(symbol)
        if not pos:
            raise ValueError(f"No open position in {symbol}")
        fraction = max(0.0, min(1.0, fraction))
        qty = pos.qty if fraction >= 0.999 else pos.qty * fraction
        fill = self._sell(symbol, qty)
        sold_frac = min(fill.qty / pos.qty, 1.0) if pos.qty else 1.0
        cost_part = pos.cost_usd * sold_frac
        proceeds = fill.value_usd - fill.fee_usd
        pnl = proceeds - cost_part
        pos.qty -= fill.qty
        pos.cost_usd -= cost_part
        pos.realized_usd += pnl
        full_close = pos.qty <= 1e-9 or sold_frac >= 0.999
        record = {
            "symbol": symbol,
            "qty": fill.qty,
            "entry_price": pos.entry_price,
            "exit_price": fill.price,
            "pnl_usd": round(pnl, 2),
            "pnl_pct": round(pnl / cost_part * 100, 3) if cost_part else 0,
            "opened_at": pos.opened_at,
            "closed_at": fill.ts,
            "reason": reason,
            "partial": not full_close,
        }
        if full_close:
            record["trade_total_pnl_usd"] = round(pos.realized_usd, 2)
            del self.positions[symbol]
        self.realized.append(record)
        self.save()
        return record

    def close(self, symbol: str, reason: str) -> dict:
        return self.reduce(symbol, 1.0, reason)

    def completed_trades(self) -> list[dict]:
        """Final records of fully closed trades (P&L includes earlier partial sells)."""
        return [r for r in self.realized if not r.get("partial")]


class PaperBroker(BaseBroker):
    def __init__(self, market: MarketData, state_path: Path, starting_cash: float,
                 fee_rate: float, slippage: float):
        super().__init__(market, state_path)
        self._cash = starting_cash
        self.starting_cash = starting_cash
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.load()

    def _extra_state(self) -> dict:
        return {"cash": self._cash, "starting_cash": self.starting_cash}

    def _load_extra(self, data: dict) -> None:
        self._cash = data.get("cash", self._cash)
        self.starting_cash = data.get("starting_cash", self.starting_cash)

    def cash(self) -> float:
        return self._cash

    def _buy(self, symbol: str, usd: float) -> Fill:
        price = self.market.price(symbol) * (1 + self.slippage)
        fee = usd * self.fee_rate
        if usd + fee > self._cash + 1e-9:
            usd = self._cash / (1 + self.fee_rate)
            fee = usd * self.fee_rate
        qty = usd / price
        self._cash -= usd + fee
        return Fill(symbol, "buy", qty, price, fee, usd, time.time())

    def _sell(self, symbol: str, qty: float) -> Fill:
        price = self.market.price(symbol) * (1 - self.slippage)
        value = qty * price
        fee = value * self.fee_rate
        self._cash += value - fee
        return Fill(symbol, "sell", qty, price, fee, value, time.time())


class LiveBroker(BaseBroker):
    """Real orders. Positions opened by the agent are tracked locally; the coin
    balance on the exchange is the source of truth for how much can be sold."""

    def __init__(self, market: MarketData, state_path: Path, quote: str):
        super().__init__(market, state_path)
        self.ex = market.ex
        self.quote = quote
        self.load()

    def _balance(self, currency: str) -> float:
        bal = self.ex.fetch_balance()
        return float((bal.get("free") or {}).get(currency) or 0.0)

    def cash(self) -> float:
        return self._balance(self.quote)

    def _fill_from_order(self, order: dict, symbol: str, side: str) -> Fill:
        oid = order.get("id")
        # Market orders may not report fills immediately; poll briefly.
        for _ in range(10):
            if order.get("filled") and order.get("average"):
                break
            time.sleep(0.5)
            order = self.ex.fetch_order(oid, symbol)
        qty = float(order.get("filled") or 0)
        price = float(order.get("average") or order.get("price") or self.market.price(symbol))
        fee = order.get("fee") or {}
        fee_cost = float(fee.get("cost") or 0)
        fee_usd = 0.0
        if fee.get("currency") == self.quote:
            fee_usd = fee_cost
        elif fee.get("currency") == symbol.split("/")[0]:
            fee_usd = fee_cost * price
            if side == "buy":
                qty -= fee_cost  # fee taken out of the coins received
        if qty <= 0:
            raise RuntimeError(f"Order {oid} for {symbol} did not fill: {order.get('status')}")
        return Fill(symbol, side, qty, price, fee_usd, qty * price, time.time(), oid)

    def _buy(self, symbol: str, usd: float) -> Fill:
        if self.ex.has.get("createMarketBuyOrderWithCost"):
            order = self.ex.create_market_buy_order_with_cost(symbol, usd)
        else:
            amount = float(self.ex.amount_to_precision(symbol, usd / self.market.price(symbol)))
            order = self.ex.create_market_buy_order(symbol, amount)
        return self._fill_from_order(order, symbol, "buy")

    def _sell(self, symbol: str, qty: float) -> Fill:
        base = symbol.split("/")[0]
        qty = min(qty, self._balance(base))  # fees may have reduced the coin balance
        amount = float(self.ex.amount_to_precision(symbol, qty))
        order = self.ex.create_market_sell_order(symbol, amount)
        return self._fill_from_order(order, symbol, "sell")
