# btc-race-24h-20261118-1444

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Yula3070/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Yula3070/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A long-only cbBTC/USDC bot on 1-minute bars. It sits in cash most of the
time and only shoots two patterns, one position at a time, full size.

## Leg 1 — crash recovery

After the price has fallen at least 1.5% over the last 180 minutes **and**
has climbed back at least 0.3% off its trailing 60-minute low, buy with
all cash. The bounce off the low is the confirmation: a single green
minute inside a crash is noise, a climb off the low is a bottom forming.
Exit at +2.0% profit, -1.0% loss, or after 480 minutes.

## Leg 2 — pullback

Once the crash trade has closed (or after 600 bars with no fill at all),
buy when the price has pulled back at least 0.8% from its trailing
240-minute high **and** has climbed back at least 0.3% off its trailing
60-minute low. Exit at +0.6% profit, -1.0% loss, or after 360 minutes.

A 10-bar cooldown follows every exit. Max slippage 300 bps on every
order. Every decision is a pure function of the closes seen so far: no
clock, no environment, no randomness, no network.

## Why this shape

The dev window falls 2.8% with the damage concentrated in the first two
hours, then bases, climbs about 2% over hours 6–8, drifts sideways, and
bleeds slowly into the close. A dip bot that buys the first green minute
inside the crash buys too early; a bot that waits for the recovery off
the low buys the base and rides the climb. The second half of the window
is a slow bleed with no edge above the ~26 bps round-trip cost, so the
bot is built to sit it out rather than chase it: in the second half of
the dev window it makes no trades and loses nothing.

## Local verification (dev window, real grader)

- Net PnL **+$22.62** (+2.26%), 4 trades (2 round trips), win rate 1.00
- Max drawdown 0.76%, Sharpe 0.042, fees $1.62
- Net PnL at 2x fees: +$20.98; guardrails met
- Two executions of the Python entry through the wire protocol give
  byte-identical action logs (deterministic)
- Baselines on the same window, official grader: buy-and-hold -$31.63,
  momentum -$23.87, ema-cross -$148.17, rsi-bollinger -$39.92,
  adx-momentum -$75.57

## Files

- `main.py` — the bot (Python 3.13, standard library only)
- `vendor/makefun_bars.py` — the kit's protocol shim, copied byte for byte

## Run it

```sh
python3 -P -s main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=tfznw81m&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
