'''
Run with -> python run_bot.py
'''

# run_bot.py
import pandas as pd
from src.config import LIQUID_POKEMON, MIN_DISCOUNT_PCT, SOL_PRICE
from src.client import Client
from src.price_aggregator import PriceAggregator
from src.analyzer import analyze


def main():
    print("Starting liquid Pokémon arbitrage scan...\n")

    # 1. Fetch listings
    me = Client(headless=False)           # Change to True for speed later
    print("Fetching listings from Collector Crypt...")
    listings = me.fetch_filtered_listings(LIQUID_POKEMON, scroll_times=25)
    me.close()
    print(f"\nFetched {len(listings)} liquid cards\n")

    # 2. Analyze w/ PriceCharting
    aggregator = PriceAggregator(headless=False)
    print(f"\nAnalyzing {len(listings)} listings with PriceCharting...\n")

    all_listings_data = []
    arbitrage_opps = []

    for i, listing in enumerate(listings, 1):
        title = listing.get("title", "")[:100]
        print(f"[{i}/{len(listings)}] {title}...")

        fair_data = aggregator.get_fair_value(title)

        # Build row for all_listings.csv
        all_row = listing.copy()
        if fair_data:
            discount_pct = round(
                (fair_data.get("average_usd", 0) - listing.get("usd_price", 0)) /
                max(fair_data.get("average_usd", 1), 1) * 100, 1
            )
            all_row.update({
                "fair_value": fair_data.get("average_usd"),
                "discount_pct": discount_pct,
                "grade": fair_data.get("grade_detected", "N/A"),
                "sources": fair_data.get("sources", "PriceCharting"),
                "pricecharting_link": fair_data.get("pricecharting_link", ""),
                "confidence": fair_data.get("confidence", 0.0),
                "matched_card": fair_data.get("matched_card", ""),
                "search_term_used": fair_data.get("search_term_used", "")
            })

        all_listings_data.append(all_row)

        # Only good deals go to arbitrage file
        result = analyze(listing, fair_data)
        if result:
            arbitrage_opps.append(result)
            print(f"Arbitrage found: {result.get('discount_pct', 0)}% below")
    
    aggregator.close()


    # Save ALL listings
    if all_listings_data:
        pd.DataFrame(all_listings_data).to_csv("all_listings.csv", index=False)
        print(f"Saved {len(all_listings_data)} total listings → all_listings.csv")

    # Save only arbitrage opportunities
    if arbitrage_opps:
        pd.DataFrame(arbitrage_opps).to_csv("arbitrage_opportunities.csv", index=False)
        print(f"Saved {len(arbitrage_opps)} arbitrage opportunities → arbitrage_opportunities.csv")
        
        best = max(arbitrage_opps, key=lambda x: x.get("discount_pct", 0))
        print(f"Best deal: {best.get('discount_pct', 0)}% on {best.get('title', '')[:80]}...")
    else:
        print("No arbitrage opportunities found above threshold.")

    return arbitrage_opps

if __name__ == "__main__":
    main()