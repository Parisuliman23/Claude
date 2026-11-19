# Day Trader: a Claude crypto day-trading agent

Claude (Opus 5.5) watches the crypto market and makes the trading calls itself.
Code around it does everything that must never go wrong: hard risk limits,
stop-losses, the daily loss cap and a kill switch.

**It starts in paper mode**: real live prices, simulated money. Nothing touches
a real account until you change `mode: live` in `config.yaml`.

## How it works

```
every 15 min ─► Claude decision cycle
                 get_account → get_market_data (several timeframes) → get_order_book
                 → open_long / close_position / update_stops → short written summary
                       │
                       ▼
                 Risk manager (code): can shrink or reject every order
                       │
                       ▼
                 Paper broker (simulated) or Live broker (real ccxt orders)

every 20 s  ─► Guard (code, no AI): sells on stop-loss / take-profit,
               halts + flattens at the daily loss limit, optional end-of-day flatten
```

Every decision, order, rejection and summary goes to `state/journal_<mode>.jsonl`.
Claude sees its own past summaries and closed trades, so it can learn from its results.

## Setup

```bash
cd daytrader
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY
```

Edit `config.yaml`: pick the exchange (`coinbase`, `kraken`, `binanceus`, ...),
the coins, the risk limits and your own `strategy_notes` for Claude.

## Run it

```bash
python -m trader.main once      # one decision cycle, to see what it does
python -m trader.main run       # keep running (Ctrl-C to stop)
python -m trader.main status    # equity, positions, P&L, win rate
python -m trader.main flatten   # sell everything now
```

Stop new trades at any time without stopping the program: `touch state/KILL`
(delete the file to resume).

## Risk rules (in code; Claude can't override them)

| Rule | Default |
|---|---|
| Stop-loss required on every trade | yes, at most 8% away |
| Max loss per trade if the stop hits | 1% of equity (orders are shrunk to fit) |
| Max in one coin / in all coins | 20% / 60% of equity |
| Daily loss limit | −2%: closes everything, no new trades until 00:00 UTC |
| Max trades per day | 10 |
| Stops can only be tightened | yes |
| Only coins in `symbols` | yes |

Spot, long-only: no leverage, no shorting.

## Going live (only after paper results convince you)

1. Run paper mode for at least a few weeks and check `status` and the journal.
2. Create an exchange API key with **trade permission only, never withdrawals**,
   and put it in `.env` (`EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET`).
3. Fund the account with an amount you can afford to lose.
4. Set `mode: live` and `paper_fee_rate` to your real fee in `config.yaml`.

Stops are enforced by this program, not placed on the exchange: **they only work
while `run` is running.** Run it on an always-on machine (a small cloud VM) and
`flatten` before shutting it down.

## Costs

Each decision cycle is a few Claude API calls. At 15-minute intervals that's
~96 cycles a day; check your usage in the Claude Console after the first day and
raise `decision_interval_minutes` or lower `effort` if it's more than you want.

## Tests

```bash
python -m pytest -q tests      # offline: fake exchange + scripted Claude, no API cost
```

## Honest warning

Most day traders lose money, and an AI deciding doesn't change the odds by
itself. Fees (~1.2% round trip at Coinbase's default rate) eat small moves.
Treat this as an experiment, judge it on paper results, and never trade money
you can't afford to lose. This is not financial advice.
