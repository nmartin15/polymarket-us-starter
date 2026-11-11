# Polymarket US Starter (Paper Trading)

A starter kit for retail traders: connect to the Polymarket US API, pull live market data, and run a paper-trading bot. The bot reads real prices but never sends a real order.

This is for Polymarket US (the CFTC-regulated app at polymarket.us). It does not work with polymarket.com, and keys from one do not work on the other.

## 1. Install

```bash
git clone <this-repo-url>
cd polymarket-us-starter
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Check the setup offline

```bash
python test_offline.py
```

This runs the bot against a fake order book. If it prints "All offline checks passed", your setup works.

## 3. Pull live market data (no key needed)

```bash
python step1_market_data.py               # list active markets
python step1_market_data.py <market-slug> # quote, spread, order book
```

## 4. Create your API key

1. Log in to Polymarket US and complete identity verification.
2. Go to polymarket.us/developer and create a key.
3. You get a Key ID and a Secret Key. The secret is shown once, so save it right away.
4. Copy `.env.example` to `.env` and paste both values in.

```bash
cp .env.example .env
python step2_check_account.py   # read-only: balance, positions, open orders
```

Key rules:
- `.env` is in `.gitignore` and `.cursorignore`. Keep it there, so it never reaches GitHub or your editor's AI.
- Never paste your secret into a chat, a screenshot, or a screen recording.
- If a key leaks, revoke it at polymarket.us/developer and make a new one.

## 5. Run the paper bot

Set these values in `.env`:
- `MARKET_SLUG`: the market to watch
- `FAIR_VALUE`: your own estimate of the YES probability (0 to 1)
- `MIN_EDGE`, `ORDER_SIZE`, `MAX_POSITION`, `MAX_DAILY_LOSS`

```bash
python step3_paper_bot.py
```

To stop it, press Ctrl+C, or create a file named `STOP` in this folder. Every paper trade is logged to `paper_trades.csv`.

## How the paper fills work

They are pessimistic on purpose:
- Buys fill at the best ask and sells fill at the best bid, so you are always the taker.
- You only get the size showing at the top of the book.
- Every fill pays the taker fee: `contracts x rate x price x (1 - price)`.
- Open positions are valued at the best bid.

If a strategy can't make money under these rules, it won't make money live.

## Fees

Polymarket US charges takers by market category, using the formula above, and makers pay nothing. Set `TAKER_FEE_RATE` to the current rate for your market's category. Check the official schedule before you trade, because it changes.

## Files

| File | What it does |
|---|---|
| `config.py` | Loads `.env` and builds the client |
| `step1_market_data.py` | Public market data |
| `step2_check_account.py` | Proves your key works (read-only) |
| `paper_broker.py` | Simulated fills, fees, and P&L |
| `step3_paper_bot.py` | Bot loop: data, signal, risk limits, kill switch |
| `test_offline.py` | Runs the bot against a fake book |

Not financial advice. Prediction markets can lose you money, and paper results do not guarantee live results.

Free for Realm Labs students. MIT licensed.
