"""Crash-recovery + pullback bot for cbBTC/USDC, 1-minute bars.

The bot sits in cash almost all the time and only shoots two patterns:

1. Crash recovery (first): after the price has fallen at least 1.5% over
   the last 180 minutes AND has climbed back at least 0.3% off its
   trailing 60-minute low, buy with all cash. The drop must be confirmed
   by the bounce off the low, not by a single green minute: buying the
   falling knife is what kills dip bots. Exit at +2.0% profit, -1.0% loss,
   or after 480 minutes, whichever comes first.

2. Pullback (after the crash trade, or after 600 bars with no fill at
   all): after the price has pulled back at least 0.8% from its trailing
   240-minute high AND has climbed back at least 0.3% off its trailing
   60-minute low, buy with all cash. Exit at +0.6% profit, -1.0% loss,
   or after 360 minutes.

A 10-bar cooldown follows every exit. One position at a time, long only,
full size, max slippage 300 bps. Every decision is a pure function of the
closes seen so far: no clock, no environment, no randomness.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
MAX_SLIPPAGE_BPS = 300

# Crash leg: 180-bar drop, recovery off the 60-bar low, exits.
CRASH_DROP_BPS = 150
CRASH_LOOKBACK = 180
CRASH_TP_BPS = 200
CRASH_SL_BPS = 100
CRASH_MAX_HOLD = 480

# Pullback leg: pullback from the 240-bar high, recovery off the 60-bar low.
PB_PULLBACK_BPS = 80
PB_HIGH_LOOKBACK = 240
PB_TP_BPS = 60
PB_SL_BPS = 100
PB_MAX_HOLD = 360

RECOVERY_BPS = 30
LOW_LOOKBACK = 60
COOLDOWN_BARS = 10
ARM_PULLBACK_BAR = 600


class Trader:
    """Keeps the closes and the position state machine."""

    def __init__(self):
        self.closes = []
        self.mode = "flat"  # flat | wait_buy | long | wait_sell
        self.phase = "crash"  # crash | pullback
        self.fill_price = None
        self.held = 0
        self.cooldown = 0
        self.ever_filled = False
        self.take_profit_bps = CRASH_TP_BPS
        self.max_hold = CRASH_MAX_HOLD

    def _lowest(self, window):
        return min(self.closes[-window:])

    def _highest(self, window):
        return max(self.closes[-window:])

    def _crash_setup(self):
        if len(self.closes) <= CRASH_LOOKBACK:
            return False
        now = self.closes[-1]
        then = self.closes[-1 - CRASH_LOOKBACK]
        if now * 10000 > then * (10000 - CRASH_DROP_BPS):
            return False
        low = self._lowest(LOW_LOOKBACK + 1)
        return now * 10000 >= low * (10000 + RECOVERY_BPS)

    def _pullback_setup(self):
        if len(self.closes) <= PB_HIGH_LOOKBACK:
            return False
        now = self.closes[-1]
        high = self._highest(PB_HIGH_LOOKBACK + 1)
        if now * 10000 > high * (10000 - PB_PULLBACK_BPS):
            return False
        low = self._lowest(LOW_LOOKBACK + 1)
        return now * 10000 >= low * (10000 + RECOVERY_BPS)

    def _apply_fills(self, batch):
        for fill in batch.get("fills", []):
            if fill.get("symbol") != SYMBOL:
                continue
            if fill.get("status") == "filled":
                if fill.get("side") == "buy":
                    self.mode = "long"
                    self.fill_price = int(fill["price"])
                    self.held = 0
                    self.ever_filled = True
                elif fill.get("side") == "sell":
                    self.mode = "flat"
                    self.cooldown = COOLDOWN_BARS
                    if self.phase == "crash":
                        self.phase = "pullback"
            elif fill.get("status") == "rejected":
                if fill.get("side") == "buy" and self.mode == "wait_buy":
                    self.mode = "flat"
                elif fill.get("side") == "sell" and self.mode == "wait_sell":
                    self.mode = "long"

    def on_batch(self, state, batch):
        if state.warming_up:
            return []
        for bar in batch.get("bars", []):
            if bar.get("symbol") == SYMBOL:
                self.closes.append(int(bar["c"]))
        self._apply_fills(batch)
        if not self.closes:
            return []
        if self.phase == "crash" and not self.ever_filled and state.seq >= ARM_PULLBACK_BAR:
            self.phase = "pullback"
        if self.mode == "flat":
            if self.cooldown > 0:
                self.cooldown -= 1
                return []
            if self.phase == "crash" and self._crash_setup():
                self.take_profit_bps = CRASH_TP_BPS
                self.max_hold = CRASH_MAX_HOLD
                self.mode = "wait_buy"
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": state.cash,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            if self.phase == "pullback" and self._pullback_setup():
                self.take_profit_bps = PB_TP_BPS
                self.max_hold = PB_MAX_HOLD
                self.mode = "wait_buy"
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": state.cash,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            return []
        if self.mode == "long":
            self.held += 1
            if self.fill_price is None:
                return []
            now = self.closes[-1]
            took_profit = now * 10000 >= self.fill_price * (10000 + self.take_profit_bps)
            stopped_out = now * 10000 <= self.fill_price * (10000 - PB_SL_BPS)
            if took_profit or stopped_out or self.held >= self.max_hold:
                holding = state.positions.get(SYMBOL)
                if holding is None or holding.qty <= 0:
                    return []
                self.mode = "wait_sell"
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            return []
        return []


TRADER = Trader()


def on_batch(state, batch):
    return TRADER.on_batch(state, batch)


makefun_bars.run(on_batch)
