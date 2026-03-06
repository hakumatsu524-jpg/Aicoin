"""
Utility functions for the AI Coin bot.
"""

import os
import logging
import sys
from pathlib import Path
from typing import Dict, Any

import yaml


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application."""
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Setup file handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    file_handler = logging.FileHandler(log_dir / "bot.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("solana").setLevel(logging.WARNING)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = Path(config_path)

    # Default configuration
    default_config = {
        "coin_address": os.getenv("COIN_ADDRESS", ""),
        "rpc_url": os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com"),
        "check_interval": 60,
        "min_confidence": 0.7,
        "max_buyback_sol": 0.5,
        "cooldown_minutes": 30,
        "min_rewards_threshold": 0.01,
        "enable_notifications": True,
    }

    if not config_file.exists():
        logging.warning(f"Config file {config_path} not found, using defaults")
        return default_config

    try:
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f) or {}

        # Merge with defaults
        config = {**default_config, **file_config}

        # Override with environment variables if set
        if os.getenv("COIN_ADDRESS"):
            config["coin_address"] = os.getenv("COIN_ADDRESS")
        if os.getenv("RPC_URL"):
            config["rpc_url"] = os.getenv("RPC_URL")

        return config

    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return default_config


def format_sol(amount: float) -> str:
    """Format SOL amount for display."""
    if amount >= 1:
        return f"{amount:.4f} SOL"
    elif amount >= 0.001:
        return f"{amount:.6f} SOL"
    else:
        return f"{amount:.9f} SOL"


def format_usd(amount: float) -> str:
    """Format USD amount for display."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.2f}K"
    elif amount >= 1:
        return f"${amount:.2f}"
    else:
        return f"${amount:.6f}"


def truncate_address(address: str, chars: int = 4) -> str:
    """Truncate a blockchain address for display."""
    if len(address) <= chars * 2 + 3:
        return address
    return f"{address[:chars]}...{address[-chars:]}"


def calculate_pnl(entry_price: float, current_price: float, quantity: float) -> Dict[str, float]:
    """Calculate profit/loss for a position."""
    value_at_entry = entry_price * quantity
    current_value = current_price * quantity
    pnl = current_value - value_at_entry
    pnl_percent = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

    return {
        "pnl": pnl,
        "pnl_percent": pnl_percent,
        "value_at_entry": value_at_entry,
        "current_value": current_value
    }
