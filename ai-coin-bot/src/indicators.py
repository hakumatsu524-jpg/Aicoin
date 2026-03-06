"""
Technical Indicators Module
Calculates various technical indicators for chart analysis.
"""

from typing import List, Dict, Optional
import statistics


class TechnicalIndicators:
    """Calculate technical indicators from OHLCV data."""

    def calculate_all(self, candles: List[Dict]) -> Dict:
        """Calculate all technical indicators."""
        if not candles or len(candles) < 2:
            return {}

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        indicators = {}

        # Moving Averages
        indicators["sma_20"] = self.sma(closes, 20)
        indicators["sma_50"] = self.sma(closes, 50)
        indicators["ema_12"] = self.ema(closes, 12)
        indicators["ema_26"] = self.ema(closes, 26)

        # RSI
        indicators["rsi"] = self.rsi(closes, 14)

        # MACD
        macd_data = self.macd(closes)
        indicators["macd"] = macd_data["macd"]
        indicators["macd_signal"] = macd_data["signal"]
        indicators["macd_histogram"] = macd_data["histogram"]

        # Bollinger Bands
        bb_data = self.bollinger_bands(closes, 20)
        indicators["bb_upper"] = bb_data["upper"]
        indicators["bb_middle"] = bb_data["middle"]
        indicators["bb_lower"] = bb_data["lower"]

        # Volume
        indicators["volume_sma"] = self.sma(volumes, 20) if volumes else 0

        # ATR (Average True Range)
        indicators["atr"] = self.atr(highs, lows, closes, 14)

        # Stochastic
        stoch = self.stochastic(highs, lows, closes, 14)
        indicators["stoch_k"] = stoch["k"]
        indicators["stoch_d"] = stoch["d"]

        return indicators

    def sma(self, data: List[float], period: int) -> float:
        """Calculate Simple Moving Average."""
        if len(data) < period:
            return data[-1] if data else 0
        return sum(data[-period:]) / period

    def ema(self, data: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return self.sma(data, len(data))

        multiplier = 2 / (period + 1)
        ema_values = [self.sma(data[:period], period)]

        for price in data[period:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])

        return ema_values[-1]

    def rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(closes) < period + 1:
            return 50.0  # Neutral default

        # Calculate price changes
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        # Separate gains and losses
        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]

        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Smooth the averages
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD indicator."""
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0}

        # Calculate MACD line
        ema_fast = self.ema(closes, fast)
        ema_slow = self.ema(closes, slow)
        macd_line = ema_fast - ema_slow

        # For signal line, we need historical MACD values
        macd_values = []
        for i in range(slow, len(closes) + 1):
            subset = closes[:i]
            ema_f = self.ema(subset, fast)
            ema_s = self.ema(subset, slow)
            macd_values.append(ema_f - ema_s)

        signal_line = self.ema(macd_values, signal) if len(macd_values) >= signal else macd_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": macd_line - signal_line
        }

    def bollinger_bands(self, closes: List[float], period: int = 20, std_dev: float = 2.0) -> Dict:
        """Calculate Bollinger Bands."""
        if len(closes) < period:
            current = closes[-1] if closes else 0
            return {"upper": current, "middle": current, "lower": current}

        middle = self.sma(closes, period)
        std = statistics.stdev(closes[-period:])

        return {
            "upper": middle + (std_dev * std),
            "middle": middle,
            "lower": middle - (std_dev * std)
        }

    def atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(closes) < 2:
            return 0

        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0

        return sum(true_ranges[-period:]) / period

    def stochastic(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Dict:
        """Calculate Stochastic Oscillator."""
        if len(closes) < period:
            return {"k": 50, "d": 50}

        # Calculate %K
        lowest_low = min(lows[-period:])
        highest_high = max(highs[-period:])

        if highest_high == lowest_low:
            k = 50
        else:
            k = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100

        # Calculate %D (3-period SMA of %K)
        # Simplified: just return current K as D for single calculation
        d = k

        return {"k": k, "d": d}

    def vwap(self, highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> float:
        """Calculate Volume Weighted Average Price."""
        if not volumes or sum(volumes) == 0:
            return closes[-1] if closes else 0

        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        vwap = sum(tp * v for tp, v in zip(typical_prices, volumes)) / sum(volumes)

        return vwap

    def support_resistance(self, highs: List[float], lows: List[float], lookback: int = 20) -> Dict:
        """Identify support and resistance levels."""
        if len(highs) < lookback:
            lookback = len(highs)

        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]

        resistance = max(recent_highs)
        support = min(recent_lows)

        return {
            "resistance": resistance,
            "support": support,
            "range": resistance - support
        }
