# Pokémon Arbitrage Bot

**Collector Crypto vs PriceCharting Arbitrage Bot on Pokémon TCG Cards**

Automated Python bot that scrapes liquid Pokémon card (`config.py`) listings from **Collector Crypto**, then it pulls accurate graded prices from **PriceCharting.com**, and flags high-confidence arbitrage opportunities.

# How to run
1. Pull data:

```python run_bot.py```

2. View dash:

```streamlit run dashboard.py```

# Project Structure
```
pokemon-arbitrage-bot/
├── run_bot.py                    # ← Main bot entry point
├── dashboard.py                  # ← Web dashboard (Streamlit)
├── src/
│   ├── config.py                 # Liquid Pokémon list + settings
│   ├── price_aggregator.py       # PriceCharting scraper & matcher
│   ├── analyzer.py               # Arbitrage logic
│   ├── me_client.py              # Collector Crypto scraper
│   └── init.py
├── all_listings.csv              # Generated: all scraped cards
├── arbitrage_opportunities.csv   # Generated: profitable flips
└── README.md
```
