"""
AI Chart Analyzer using OpenAI GPT-4
Analyzes price patterns and determines buyback decisions.
"""

import os
import json
import logging
from typing import Dict, List, Any

from openai import OpenAI

from .indicators import TechnicalIndicators


class AIAnalyzer:
    """Analyzes chart data using GPT-4 to make buyback decisions."""

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger("AIAnalyzer")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.indicators = TechnicalIndicators()

    async def analyze(self, price_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze price data and return buyback decision.

        Args:
            price_data: List of OHLCV candles

        Returns:
            Dictionary with decision, confidence, and reasoning
        """
        # Calculate technical indicators
        indicators = self.indicators.calculate_all(price_data)

        # Prepare data summary for AI
        data_summary = self._prepare_data_summary(price_data, indicators)

        # Get AI decision
        decision = await self._get_ai_decision(data_summary)

        return decision

    def _prepare_data_summary(self, price_data: List[Dict], indicators: Dict) -> str:
        """Prepare a summary of the data for the AI to analyze."""
        if not price_data:
            return "No price data available"

        latest = price_data[-1]
        oldest = price_data[0]

        # Calculate price change
        price_change = ((latest["close"] - oldest["close"]) / oldest["close"]) * 100

        # Recent price action (last 10 candles)
        recent_prices = [c["close"] for c in price_data[-10:]]
        recent_high = max(recent_prices)
        recent_low = min(recent_prices)

        summary = f"""
CHART ANALYSIS FOR AI COIN (PUMPFUN)

CURRENT PRICE DATA:
- Current Price: ${latest['close']:.8f}
- 24h High: ${max(c['high'] for c in price_data[-24:]):.8f}
- 24h Low: ${min(c['low'] for c in price_data[-24:]):.8f}
- Price Change (period): {price_change:+.2f}%
- Current Volume: {latest.get('volume', 0):.2f}

TECHNICAL INDICATORS:
- RSI (14): {indicators.get('rsi', 'N/A'):.2f}
- MACD: {indicators.get('macd', 'N/A'):.6f}
- MACD Signal: {indicators.get('macd_signal', 'N/A'):.6f}
- MACD Histogram: {indicators.get('macd_histogram', 'N/A'):.6f}
- SMA 20: ${indicators.get('sma_20', 0):.8f}
- SMA 50: ${indicators.get('sma_50', 0):.8f}
- EMA 12: ${indicators.get('ema_12', 0):.8f}
- Bollinger Upper: ${indicators.get('bb_upper', 0):.8f}
- Bollinger Lower: ${indicators.get('bb_lower', 0):.8f}
- Volume SMA: {indicators.get('volume_sma', 0):.2f}

RECENT PRICE ACTION:
- Recent High: ${recent_high:.8f}
- Recent Low: ${recent_low:.8f}
- Price vs SMA20: {'Above' if latest['close'] > indicators.get('sma_20', 0) else 'Below'}
- RSI Zone: {'Oversold' if indicators.get('rsi', 50) < 30 else 'Overbought' if indicators.get('rsi', 50) > 70 else 'Neutral'}

LAST 5 CANDLES (newest first):
"""
        for candle in reversed(price_data[-5:]):
            change = ((candle["close"] - candle["open"]) / candle["open"]) * 100
            summary += f"  O:{candle['open']:.8f} H:{candle['high']:.8f} L:{candle['low']:.8f} C:{candle['close']:.8f} ({change:+.2f}%)\n"

        return summary

    async def _get_ai_decision(self, data_summary: str) -> Dict[str, Any]:
        """Get buyback decision from GPT-4."""
        system_prompt = """You are an AI trading analyst for a cryptocurrency buyback bot. 
Your task is to analyze chart data and decide whether NOW is a good time to execute a buyback.

STRATEGY CONTEXT:
- This is a buyback bot for a PumpFun memecoin called "AI Coin"
- Buybacks support the token price and reward holders
- We want to buy when price is relatively low or showing reversal signals
- Avoid buying during pumps or when price is overextended

DECISION CRITERIA:
- BUY: Price is at support, oversold RSI, bullish divergence, or accumulation phase
- HOLD: Neutral conditions, unclear direction, or already overbought
- Consider volume, momentum, and trend alignment

IMPORTANT: Be conservative. Only recommend BUY with high confidence when multiple indicators align.

Respond in JSON format:
{
    "decision": "BUY" or "HOLD",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of your decision"
}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data_summary}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )

            result = json.loads(response.choices[0].message.content)

            # Validate response structure
            if "decision" not in result:
                result["decision"] = "HOLD"
            if "confidence" not in result:
                result["confidence"] = 0.0
            if "reasoning" not in result:
                result["reasoning"] = "Unable to determine"

            # Ensure decision is valid
            if result["decision"] not in ["BUY", "HOLD"]:
                result["decision"] = "HOLD"

            # Clamp confidence
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

            return result

        except Exception as e:
            self.logger.error(f"AI analysis error: {e}")
            return {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Analysis error: {str(e)}"
            }
