# Polymarket US Starter

The free code for a three-video series from Realm Labs. It takes you from a Polymarket US account to a professional trading engine, and it only ever paper trades. Nothing in this repo can place a real order.

This is for Polymarket US (the CFTC-regulated app at polymarket.us). It does not work with polymarket.com, and keys from one do not work on the other.

| Video | Folder | What you build |
|---|---|---|
| 1. Setup | `video1_setup/` | API key, live market data, account check |
| 2. Data plumbing and paper trading | `video2_data_paper/` | Record the order book, store it as Parquet, replay it, run a live paper bot |
| 3. A professional engine | `video3_nautilus/` | Feed your US data into NautilusTrader, backtest taker and maker strategies, paper trade live |

## Before you start

You need two things:

1. **Python 3.12 or newer.** Download it from [python.org/downloads](https://www.python.org/downloads/). On Windows, tick "Add Python to PATH" in the installer.
2. **A verified Polymarket US account.** Sign up in the Polymarket US app and finish identity verification.

## Video 1: Setup

**Watch the video first.** Then do these five steps on your own. They take about 15 minutes.

1. **Download the code.** Click the green **Code** button on this page, then **Download ZIP**, and unzip it. (If you use git: `git clone https://github.com/nmartin15/polymarket-us-starter`.)
2. **Open a terminal in that folder and install.** On a Mac, if `python` isn't found, type `python3` for the first command.
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Check your setup.** `python check_everything.py` should end with "All offline checks passed".
4. **Create your API key** at polymarket.us/developer. The secret is shown once, so save it right away.
5. **Add your key.** Copy `.env.example` to a new file named `.env` and paste in your Key ID and Secret Key.

Now run the two scripts from the video:

```bash
python video1_setup/step1_market_data.py               # list active markets (no key needed)
python video1_setup/step1_market_data.py <market-slug> # rules, quote, spread, order book
python video1_setup/step2_check_account.py             # read-only: proves your key works
```

Key rules:
- `.env` is in `.gitignore`. Keep it there.
- Never paste your secret into a chat, a screenshot, or a screen recording.
- If a key leaks, revoke it at polymarket.us/developer and make a new one.

## Video 2: Data plumbing and paper trading

**Watch the video first.** Then:

1. Try every step on fake data:
   ```bash
   python video2_data_paper/make_sample_data.py
   python video2_data_paper/step2_to_parquet.py sample-market
   python video2_data_paper/step3_explore.py sample-market
   python video2_data_paper/step4_replay.py sample-market --fair 0.55
   ```
   The sample prices are invented. Never judge a strategy on them.
2. Record a real market (polling needs no key, `--stream` needs your key and catches every update):
   ```bash
   python video2_data_paper/step1_record.py <slug>
   python video2_data_paper/step1_record.py <slug> --stream
   ```
3. Convert, explore, and replay your recording with the same commands, using your slug instead of `sample-market`.
4. Set `MARKET_SLUG` and `FAIR_VALUE` (your own probability for YES) in `.env`, then run the live paper bot:
   ```bash
   python video2_data_paper/step5_paper_bot.py
   ```
   Stop it with Ctrl+C, or create a file named `STOP` in this folder. Every paper trade goes to `paper_trades.csv`.

Paper fills are pessimistic on purpose: you always cross the spread, you only get the size showing at the top of the book, and every fill pays the taker fee.

## Video 3: A professional engine

[NautilusTrader](https://nautilustrader.io) is an open-source trading engine with a Rust core and a Python API. It has no Polymarket US connector, so `us_bridge.py` supplies one for data: it turns your recordings into a Nautilus instrument, order book, and trade ticks, and adds the Polymarket US fee model.

**Watch the video first.** Then:

1. Install the engine and check it:
   ```bash
   pip install -r video3_nautilus/requirements.txt
   python check_everything.py --video3
   ```
2. Backtest on the sample data, then on your own recording:
   ```bash
   python video3_nautilus/step1_backtest.py sample-market --fair 0.55
   python video3_nautilus/step1_backtest.py <slug>
   ```
3. Paper trade live on the engine:
   ```bash
   python video3_nautilus/step2_live_paper.py            # taker
   python video3_nautilus/step2_live_paper.py --maker    # maker
   ```

Two strategies ship in `strategies.py`. The taker crosses the spread and pays the fee. The maker rests limit orders and pays no fee, but only fills when someone trades with it.

What a backtest cannot tell you:
- It cannot show how the market would have reacted to your orders.
- Maker fills are optimistic. The engine does not know how many orders were ahead of yours in the queue.
- A recording made by polling misses everything between snapshots. Use `--stream` for serious work.

## Fees

Polymarket US charges takers `contracts x rate x price x (1 - price)`, by market category, and makers pay nothing. Set `TAKER_FEE_RATE` in `.env` to the current rate for your market's category. Check the official schedule before you trade, because it changes.

## Files

| File | What it does |
|---|---|
| `pmus/config.py` | Loads `.env` and builds the API client |
| `pmus/strategy.py` | The fair-value rule and the fee formula |
| `pmus/paper_broker.py` | Simulated fills, fees, and P&L |
| `pmus/recording.py` | Reads and writes recorded market data |
| `video3_nautilus/us_bridge.py` | Polymarket US data to NautilusTrader objects |
| `video3_nautilus/strategies.py` | Taker and maker strategies for NautilusTrader |
| `check_everything.py` | Runs the whole series offline |

Free for Realm Labs students. MIT licensed. NautilusTrader is a separate project under LGPL-3.0.

Not financial advice. Prediction markets can lose you money, and paper or backtest results do not guarantee live results.
