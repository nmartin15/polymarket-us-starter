# Polymarket US Starter

Free code for a three-video series from Realm Labs: connect your personal Polymarket US account to Python, read markets, watch your account live, and place a small order the right way.

## Which Polymarket API is this?

Polymarket US has two trading APIs. Pick the one that matches who you are.

| | **Retail API** (this repo) | **Institutional API** ([Trader Guide](https://docs.polymarket.us/trader-guide/overview)) |
|---|---|---|
| Who it's for | Anyone with a personal Polymarket US account, including people automating their own trading | Firms Polymarket onboards: market makers, brokers, funds |
| How you get in | The iPhone app, then one key from polymarket.us/developer | Polymarket onboarding: Client ID, JWT private key, pre-production environment |
| How you connect | Official Python SDK (REST) and two WebSockets | REST, gRPC, or FIX |
| Account ID | Never. Your key implies your account | Every call names an `accountId` |

A key from polymarket.us/developer does not open the institutional API. If you trade your own money, you're on the retail side, even with a fully automated strategy. The institutional API will get its own video.

It's also different from polymarket.com, Polymarket's international crypto product. Tutorials for that one use wallets and blockchain keys. Ignore them here.

## The path, in the order you'll hit it

| # | Step | Video | Script |
|---|---|---|---|
| 1 | Phone: install the iOS app, get approved, fund your account | 1 | none |
| 2 | One key from polymarket.us/developer, into `.env` | 1 | `video1_setup/step3_check_key.py` |
| 3 | Public market data, no key: series, events, markets, book | 1 | `video1_setup/step1_browse.py`, `step2_market.py` |
| 4 | Your account over REST: balances, positions, open orders | 2 | `video2_account_live/step1_account.py` |
| 5 | Markets WebSocket: live book, prices, trades, heartbeats | 2 | `video2_account_live/step2_market_stream.py` |
| 6 | Private WebSocket: your orders, fills, positions, balance live | 2 | `video2_account_live/step3_private_stream.py` |
| 7 | Orders: preview, then one tiny real order, then cancel | 3 | `video3_orders/step1_preview.py`, `step2_place_and_cancel.py` |

## Before you start

- **An iPhone** for the Polymarket US app.
- **A computer with Python 3.10 or newer** ([python.org/downloads](https://www.python.org/downloads/); on Windows, tick "Add Python to PATH").

## Video 1: Account, key, and market data

**Watch the video first.** Then:

### On your iPhone
1. Download **Polymarket US** from the App Store and sign up.
2. Finish identity verification (legal name, date of birth, phone, address, SSN; some people are also asked for an ID photo and a selfie) and wait for the in-app approval.
3. Fund your account from **Portfolio → Deposit**.

If the app asks for an invite code, email support@polymarket.us. Polymarket US isn't available in Nevada.

### In your web browser
1. Go to [polymarket.us/developer](https://polymarket.us/developer) and sign in with the same login you use on your phone.
2. Create a key. You get a **Key ID** and a **Secret Key**. Copy the secret now; it's shown once.

### On your computer
1. Download this repo: green **Code** button, then **Download ZIP**, and unzip it.
2. Open a terminal in that folder (on a Mac, use `python3` if `python` isn't found):
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python check_everything.py       # should end with "All offline checks passed"
   ```
3. Copy `.env.example` to `.env` and paste in your Key ID and Secret Key.
4. Run it:
   ```bash
   python video1_setup/step1_browse.py                       # series
   python video1_setup/step1_browse.py --series <ID>         # events in a series
   python video1_setup/step1_browse.py --event <event-slug>  # markets in an event
   python video1_setup/step2_market.py <market-slug>         # one market, explained
   python video1_setup/step3_check_key.py                    # "Key works."
   ```

**Reading a market.** Each market is one instrument with a YES (long) side and a NO (short) side. In a two-team slug, the first team is YES. Read the price step (`orderPriceMinTickSize`, often 0.005) and the smallest order (`minimumTradeQty`, often 0.01 contracts) from the market itself; never guess them from the slug. `step2_market.py` prints both.

## Video 2: Your account, live

```bash
python video2_account_live/step1_account.py                 # balances, positions, open orders (REST)
python video2_account_live/step2_market_stream.py <slug>    # live book, trades, heartbeats
python video2_account_live/step3_private_stream.py          # your orders, fills, positions, balance
```

- Positions are a map keyed by market, and the net position can be negative: that's a short.
- Shorts lock $1.00 of margin per contract, which is why buying power can be lower than cash.
- Don't poll. The WebSockets replace repeated REST calls and keep you under the rate limit.
- The private socket is how you know an order filled. REST is your check that nothing was missed; `step3_private_stream.py` runs that check when you stop it.

## Video 3: Orders

```bash
python video3_orders/step1_preview.py <slug> buy-yes 0.45 1                  # preview only
python video3_orders/step2_place_and_cancel.py <slug> buy-yes 0.05 1         # dry run
python video3_orders/step2_place_and_cancel.py <slug> buy-yes 0.05 1 --live  # real
```

| Action | Intent | You think in | `price.value` you send |
|---|---|---|---|
| `buy-yes` | `ORDER_INTENT_BUY_LONG` | YES price | YES price |
| `sell-yes` | `ORDER_INTENT_SELL_LONG` | YES price | YES price |
| `buy-no` | `ORDER_INTENT_BUY_SHORT` | NO price | 1 - NO price |
| `sell-no` | `ORDER_INTENT_SELL_SHORT` | NO price | 1 - NO price |

`price.value` is always the YES price. The script converts it for you.

Guard rails on real orders: nothing is sent without `--live`, you must type `PLACE`, the size is capped by `MAX_LIVE_CONTRACTS` (default 1), the order is maker-only so it rests instead of crossing the spread, and it's cancelled after `HOLD_SECONDS`. Run the private stream in a second terminal to watch it happen.

## Fees

Takers pay `Θ × contracts × price × (1 − price)`, rounded to the cent. Θ is your account's tier by 30-day taker volume:

| 30-day taker volume | Θ |
|---|---|
| Under $10,000 | 9.5% |
| $10,000 to $50,000 | 8.5% |
| $50,000 to $250,000 | 7.5% |
| $250,000 and up | 6.95% |

New accounts pay 6.95% for their first 7 days. Makers pay no fee and earn a small rebate. Market objects also carry a `feeCoefficient`, which `step2_market.py` prints. Check the [official fee schedule](https://docs.polymarket.us/fees) before you trade.

## Key safety

- `.env` is in `.gitignore`. Keep it there.
- Never paste your secret into a chat, a screenshot, or a screen recording.
- If a key leaks, revoke it at polymarket.us/developer and make a new one.

## Files

| File | What it does |
|---|---|
| `pmus/config.py` | Loads `.env` and builds the SDK clients |
| `pmus/money.py` | Prices as USD objects, price and quantity steps, the fee formula |
| `pmus/markets.py` | Reads a market: YES and NO sides, tick, minimum order, best bid and ask |
| `pmus/orders.py` | Builds an order: intent, YES-price conversion, checks |
| `pmus/live.py` | WebSocket heartbeats and reconnects |
| `check_everything.py` | Runs every script offline against a fake Polymarket |

Official docs: [docs.polymarket.us](https://docs.polymarket.us). Free for Realm Labs students. MIT licensed. Not financial advice: prediction markets can lose you money.
