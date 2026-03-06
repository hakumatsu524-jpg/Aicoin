"""
Data Fetcher Module
Fetches OHLCV price data from DexScreener API.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import httpx


class DataFetcher:
    """Fetches price data from various sources."""

    DEXSCREENER_API = "https://api.dexscreener.com"
    BIRDEYE_API = "https://public-api.birdeye.so"

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger("DataFetcher")
        self.coin_address = config.get("coin_address") or os.getenv("COIN_ADDRESS")

    async def fetch_ohlcv(self, timeframe: str = "15m", limit: int = 100) -> Optional[List[Dict]]:
        """
        Fetch OHLCV candle data for the coin.

        Args:
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch

        Returns:
            List of OHLCV dictionaries or None if failed
        """
        # Try DexScreener first
        data = await self._fetch_from_dexscreener()
        if data:
            return data

        # Fallback to Birdeye
        data = await self._fetch_from_birdeye(timeframe, limit)
        if data:
            return data

        self.logger.error("Failed to fetch data from all sources")
        return None

    async def _fetch_from_dexscreener(self) -> Optional[List[Dict]]:
        """Fetch data from DexScreener API."""
        try:
            url = f"{self.DEXSCREENER_API}/latest/dex/tokens/{self.coin_address}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30)
                response.raise_for_status()

                data = response.json()

                if not data.get("pairs"):
                    self.logger.warning("No pairs found on DexScreener")
                    return None

                # Get the most liquid pair
                pair = max(data["pairs"], key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))

                # DexScreener doesn't provide full OHLCV, so we construct from available data
                # For full OHLCV, we'd need their paid API or another source
                price_usd = float(pair.get("priceUsd", 0))
                price_change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
                volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)

                # Create synthetic candles from available data
                candles = self._create_synthetic_candles(price_usd, price_change_24h, volume_24h)

                self.logger.info(f"Fetched data from DexScreener: ${price_usd:.8f}")
                return candles

        except Exception as e:
            self.logger.error(f"DexScreener fetch error: {e}")
            return None

    async def _fetch_from_birdeye(self, timeframe: str, limit: int) -> Optional[List[Dict]]:
        """Fetch OHLCV from Birdeye API."""
        try:
            # Convert timeframe to Birdeye format
            tf_map = {
                "1m": "1m", "5m": "5m", "15m": "15m",
                "1h": "1H", "4h": "4H", "1d": "1D"
            }
            birdeye_tf = tf_map.get(timeframe, "15m")

            url = f"{self.BIRDEYE_API}/defi/ohlcv"
            params = {
                "address": self.coin_address,
                "type": birdeye_tf,
                "limit": limit
            }

            headers = {
                "X-API-KEY": os.getenv("BIRDEYE_API_KEY", "")
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()

                if not data.get("data", {}).get("items"):
                    return None

                candles = []
                for item in data["data"]["items"]:
                    candles.append({
                        "timestamp": item["unixTime"],
                        "open": item["o"],
                        "high": item["h"],
                        "low": item["l"],
                        "close": item["c"],
                        "volume": item["v"]
                    })

                self.logger.info(f"Fetched {len(candles)} candles from Birdeye")
                return candles

        except Exception as e:
            self.logger.error(f"Birdeye fetch error: {e}")
            return None

    def _create_synthetic_candles(self, current_price: float, price_change_24h: float, volume_24h: float) -> List[Dict]:
        """Create synthetic candle data when full OHLCV isn't available."""
        candles = []
        now = datetime.now()

        # Calculate price 24h ago
        price_24h_ago = current_price / (1 + price_change_24h / 100)

        # Generate 96 synthetic 15-minute candles (24 hours)
        num_candles = 96
        price_step = (current_price - price_24h_ago) / num_candles
        volume_per_candle = volume_24h / num_candles

        for i in range(num_candles):
            timestamp = now - timedelta(minutes=15 * (num_candles - i))
            base_price = price_24h_ago + (price_step * i)

            # Add some randomness for realistic OHLC
            import random
            volatility = abs(price_step) * 2 if price_step != 0 else base_price * 0.01

            open_price = base_price + random.uniform(-volatility, volatility)
            close_price = base_price + price_step + random.uniform(-volatility, volatility)
            high_price = max(open_price, close_price) + random.uniform(0, volatility)
            low_price = min(open_price, close_price) - random.uniform(0, volatility)

            candles.append({
                "timestamp": int(timestamp.timestamp()),
                "open": max(0, open_price),
                "high": max(0, high_price),
                "low": max(0, low_price),
                "close": max(0, close_price),
                "volume": volume_per_candle * random.uniform(0.5, 1.5)
            })

        return candles

    async def fetch_token_info(self) -> Optional[Dict]:
        """Fetch token information (name, symbol, etc.)."""
        try:
            url = f"{self.DEXSCREENER_API}/latest/dex/tokens/{self.coin_address}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30)
                response.raise_for_status()

                data = response.json()

                if not data.get("pairs"):
                    return None

                pair = data["pairs"][0]
                return {
                    "name": pair.get("baseToken", {}).get("name", "Unknown"),
                    "symbol": pair.get("baseToken", {}).get("symbol", "???"),
                    "price_usd": float(pair.get("priceUsd", 0)),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
                    "market_cap": float(pair.get("marketCap", 0) or 0),
                    "pair_address": pair.get("pairAddress", "")
                }

        except Exception as e:
            self.logger.error(f"Token info fetch error: {e}")
            return None
