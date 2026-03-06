# AI Coin - Intelligent PumpFun Buyback Bot

![AI Coin Logo](./assets/logo.png)

An AI-powered trading bot that analyzes PumpFun coin charts and automatically executes buybacks using creator rewards based on intelligent chart pattern analysis.

## Features

- **AI Chart Analysis**: Uses OpenAI GPT-4 to analyze price movements, volume patterns, and market sentiment
- **Automatic Buyback Execution**: Executes strategic buybacks on Solana when favorable conditions are detected
- **Creator Rewards Integration**: Utilizes accumulated creator rewards for buyback operations
- **Real-time Monitoring**: Continuously monitors chart data from PumpFun/DexScreener APIs
- **Risk Management**: Configurable thresholds and position sizing

## How It Works

1. **Data Collection**: Fetches real-time OHLCV data from DexScreener API
2. **Pattern Analysis**: Calculates technical indicators (RSI, MACD, Moving Averages, Volume)
3. **AI Decision Making**: GPT-4 analyzes the data and determines optimal buyback timing
4. **Execution**: When conditions are met, executes buyback transactions on Solana

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-coin-bot.git
cd ai-coin-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## Configuration

Edit the `.env` file with your credentials:

```env
OPENAI_API_KEY=your_openai_api_key
SOLANA_PRIVATE_KEY=your_wallet_private_key
COIN_ADDRESS=your_pumpfun_coin_address
RPC_URL=https://api.mainnet-beta.solana.com
```

## Usage

```bash
# Run the bot
python main.py

# Run with custom config
python main.py --config config.yaml

# Run in dry-run mode (no actual transactions)
python main.py --dry-run
```

## Project Structure

```
ai-coin-bot/
├── main.py                 # Entry point
├── config.yaml             # Bot configuration
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── assets/
│   └── logo.png           # AI Coin logo
└── src/
    ├── __init__.py
    ├── analyzer.py        # AI chart analysis
    ├── data_fetcher.py    # Price data fetching
    ├── executor.py        # Solana transaction execution
    ├── indicators.py      # Technical indicators
    └── utils.py           # Helper functions
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `check_interval` | Seconds between analysis cycles | 60 |
| `min_confidence` | Minimum AI confidence to execute | 0.7 |
| `max_buyback_sol` | Maximum SOL per buyback | 0.5 |
| `cooldown_minutes` | Minutes between buybacks | 30 |
| `enable_notifications` | Log detailed decisions | true |

## Risk Disclaimer

This bot is for educational purposes. Trading cryptocurrencies involves significant risk. Never invest more than you can afford to lose. The AI's decisions are not financial advice.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
