#!/usr/bin/env python3
"""
AI Coin - Intelligent PumpFun Buyback Bot
Main entry point for the trading bot.
"""

import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.data_fetcher import DataFetcher
from src.analyzer import AIAnalyzer
from src.executor import SolanaExecutor
from src.utils import setup_logging, load_config

# Load environment variables
load_dotenv()


class AICoinBot:
    """Main bot class that orchestrates the buyback strategy."""

    def __init__(self, config_path: str = "config.yaml", dry_run: bool = False):
        self.config = load_config(config_path)
        self.dry_run = dry_run
        self.logger = logging.getLogger("AICoinBot")

        # Initialize components
        self.data_fetcher = DataFetcher(self.config)
        self.analyzer = AIAnalyzer(self.config)
        self.executor = SolanaExecutor(self.config, dry_run=dry_run)

        # State tracking
        self.last_buyback_time = None
        self.total_buybacks = 0
        self.total_sol_spent = 0.0

    async def run(self):
        """Main bot loop."""
        self.logger.info("=" * 50)
        self.logger.info("AI Coin Buyback Bot Started")
        self.logger.info(f"Monitoring: {self.config['coin_address']}")
        self.logger.info(f"Dry Run Mode: {self.dry_run}")
        self.logger.info("=" * 50)

        while True:
            try:
                await self.analysis_cycle()
            except Exception as e:
                self.logger.error(f"Error in analysis cycle: {e}")

            # Wait for next cycle
            await asyncio.sleep(self.config.get("check_interval", 60))

    async def analysis_cycle(self):
        """Single cycle of data fetch, analysis, and potential execution."""
        self.logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting analysis cycle...")

        # Step 1: Fetch latest price data
        price_data = await self.data_fetcher.fetch_ohlcv()
        if not price_data:
            self.logger.warning("Failed to fetch price data, skipping cycle")
            return

        # Step 2: Get current creator rewards balance
        rewards_balance = await self.executor.get_rewards_balance()
        self.logger.info(f"Creator rewards balance: {rewards_balance:.4f} SOL")

        if rewards_balance < self.config.get("min_rewards_threshold", 0.01):
            self.logger.info("Insufficient rewards for buyback")
            return

        # Step 3: Check cooldown
        if not self._check_cooldown():
            self.logger.info("Still in cooldown period, skipping execution")
            return

        # Step 4: AI Analysis
        analysis = await self.analyzer.analyze(price_data)
        self.logger.info(f"AI Analysis Complete:")
        self.logger.info(f"  - Decision: {analysis['decision']}")
        self.logger.info(f"  - Confidence: {analysis['confidence']:.2%}")
        self.logger.info(f"  - Reasoning: {analysis['reasoning']}")

        # Step 5: Execute if conditions met
        if self._should_execute(analysis, rewards_balance):
            await self._execute_buyback(analysis, rewards_balance)

    def _check_cooldown(self) -> bool:
        """Check if cooldown period has passed since last buyback."""
        if self.last_buyback_time is None:
            return True

        cooldown_minutes = self.config.get("cooldown_minutes", 30)
        elapsed = (datetime.now() - self.last_buyback_time).total_seconds() / 60
        return elapsed >= cooldown_minutes

    def _should_execute(self, analysis: dict, rewards_balance: float) -> bool:
        """Determine if buyback should be executed based on analysis."""
        if analysis["decision"] != "BUY":
            return False

        min_confidence = self.config.get("min_confidence", 0.7)
        if analysis["confidence"] < min_confidence:
            self.logger.info(f"Confidence {analysis['confidence']:.2%} below threshold {min_confidence:.2%}")
            return False

        return True

    async def _execute_buyback(self, analysis: dict, rewards_balance: float):
        """Execute the buyback transaction."""
        # Calculate buyback amount
        max_buyback = self.config.get("max_buyback_sol", 0.5)
        buyback_amount = min(rewards_balance * 0.8, max_buyback)  # Use 80% of rewards, capped

        self.logger.info(f"Executing buyback of {buyback_amount:.4f} SOL...")

        try:
            tx_signature = await self.executor.execute_buyback(buyback_amount)

            if tx_signature:
                self.last_buyback_time = datetime.now()
                self.total_buybacks += 1
                self.total_sol_spent += buyback_amount

                self.logger.info(f"Buyback successful!")
                self.logger.info(f"  - TX: {tx_signature}")
                self.logger.info(f"  - Amount: {buyback_amount:.4f} SOL")
                self.logger.info(f"  - Total buybacks: {self.total_buybacks}")
                self.logger.info(f"  - Total SOL spent: {self.total_sol_spent:.4f}")
            else:
                self.logger.error("Buyback execution failed")

        except Exception as e:
            self.logger.error(f"Buyback execution error: {e}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AI Coin Buyback Bot")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without executing actual transactions"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)

    # Create and run bot
    bot = AICoinBot(config_path=args.config, dry_run=args.dry_run)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
