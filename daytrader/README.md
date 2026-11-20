# Day Trader: a Claude momentum day-trading agent (Ross Cameron style)

Claude trades small-cap US stocks using Ross Cameron's (Warrior Trading)
momentum strategy. Code around it enforces his discipline rules, so a bad call
stays small.

**It starts in paper mode** on your free Alpaca paper account: real market
data, fake money. Nothing touches real money until you set `mode: live`.

Strategy notes the agent is built on: [strategy/ross_cameron_playbook.md](strategy/ross_cameron_playbook.md)

## How it works

```
7:00-11:00 ET (his trading window)

every 5 min  ─► Claude: scan_momentum (5 pillars) → news → 1m/5m charts
                → picks a watchlist → buys only if a setup is triggering

every 15 s   ─► Code watches the watchlist's 1-minute charts. When a stock forms a
                first pullback and the first candle makes a new high (above VWAP,
                MACD open, light-volume pullback) → wakes Claude to decide

every 5 s    ─► Code guard (no AI):
                · stop hit → sell
                · first target hit → sell half, stop to break-even
                · still below entry after 5 min → "breakout or bailout" sell
                · window over / daily loss hit → sell everything
```

### The 5 pillars (scanner)
| Pillar | Rule |
|---|---|
| Price | $1-$20 (sweet spot $5-$10) |
| % change | up ≥10% today |
| Relative volume | ≥5× the average |
| Catalyst | news preferred; no-news movers get half size; buyouts/mergers skipped |
| Float | <20M shares (needs a free FMP key to check) |

### Entry, stop, exit
- **Entry:** first pullback after the first move up. Buy when a green candle breaks
  the high of the previous red pullback candle.
- **Stop:** low of the pullback.
- **Target:** about 2× the risk. Half is sold there and the stop moves to break-even.
- **Only when:** above VWAP, MACD above its signal line, 9 EMA above 20 EMA, and the
  pullback on lighter volume.

### Discipline rules (code enforces them; Claude can't override)
| Rule | Default |
|---|---|
| Trade window | 7:00-11:00 ET; positions closed when it ends |
| Max loss per trade | 1% of equity (orders are sized to fit) |
| Starter size | ¼ size until up 20¢/share on it, then full size (Ross's fix that gave him 45 green days in a row) |
| 3 losers in a row | done for the day |
| Max daily loss | −2%: done, everything sold |
| Give back half the day's peak profit | done for the day |
| Max trades per day | 6 |
| Stops | required, can only be raised |
| Only stocks that passed the scanner | yes |
| No shorting | long only |

## Setup

1. Make a free account at **alpaca.markets** and open the **Paper Trading**
   dashboard. Generate API keys there.
2. Optional: free API key at **financialmodelingprep.com** for float data.
3. Install and configure:
   ```bash
   cd daytrader
   pip install -r requirements.txt
   cp .env.example .env     # add ANTHROPIC_API_KEY, APCA_API_KEY_ID, APCA_API_SECRET_KEY (+ FMP_API_KEY)
   ```

## Run it

```bash
python -m trader.main scan      # today's scanner results (no Claude, no trades)
python -m trader.main once      # one Claude cycle
python -m trader.main run       # run the whole morning (start it before 7:00 ET)
python -m trader.main status    # equity, accuracy, avg win / avg loss, P/L ratio
python -m trader.main flatten   # sell everything now
```

Block new trades any time without stopping it: `touch state/KILL`.

## Good to know

- **Free data is IEX only** (`stocks_data_feed: iex`), a slice of total market volume.
  Prices are fine; volume numbers are smaller than what Ross sees. A paid Alpaca data plan
  (`sip`) gives full volume.
- **No Level 2.** Alpaca gives the best bid/ask only, not the full order book or tape
  Ross reads. The agent uses candles, volume and the quote.
- **Stops run in this program.** They only work while `run` is running. Run it on a
  computer or small cloud server that stays on all morning.
- **Pattern-day-trader rules:** under $25k in a US margin account, brokers limit day
  trades. Check Alpaca's current rules before going live. Paper is unaffected.
- **Claude API cost:** a cycle every 5 minutes for 4 hours, plus setup alerts, is roughly
  50-80 calls a morning. Check your usage after day one.

## Going live: Ross's rule

1. Paper trade **one trade a day** for at least 10 days (`max_trades_per_day: 1`).
2. `python -m trader.main status` shows whether you met his bar: **net profit above zero,
   accuracy 60% or more, average win bigger than average loss.**
3. Only then: live Alpaca keys, `mode: live`, and **tiny size** for another 10 days. Losses
   should feel like nothing. Then raise share size before raising the number of trades.

## Tests

```bash
python -m pytest -q tests     # offline: fake markets + scripted Claude, no API cost
```

## Honest warning

Ross says his results are "not typical." Most day traders lose money. This is
an experiment: judge it on paper results first. Not financial advice.
