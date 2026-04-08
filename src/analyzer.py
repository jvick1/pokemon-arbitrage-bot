# src/analyzer.py
from .config import MIN_DISCOUNT_PCT
from typing import Dict, Optional

def analyze(listing: Dict, fair_value_data: Dict) -> Dict | None:
    if not fair_value_data:
        return None
    
    me_price = listing.get("usd_price", 0)
    fair = fair_value_data.get("average_usd", 0)
    
    if fair <= 0:
        return None
    
    discount_pct = (fair - me_price) / fair * 100
    
    if discount_pct < MIN_DISCOUNT_PCT:
        return None
    
    return {
        "title": listing.get("title"),
        "usd_price": round(me_price, 2),
        "raw_price": listing.get("raw_price", me_price),
        "currency": listing.get("currency", "SOL"),
        "fair_value": round(fair, 2),
        "discount_pct": round(discount_pct, 1),
        "sources": fair_value_data.get("sources", "PriceCharting"),
        "grade": fair_value_data.get("grade_detected", "N/A"),
        "listing_url": listing.get("listing_url"),
        "image_url": listing.get("image_url", ""),
        "pricecharting_link": fair_value_data.get("pricecharting_link", ""),
        "confidence": fair_value_data.get("confidence", 0.0),
        "matched_card": fair_value_data.get("matched_card", ""),
        "search_term_used": fair_value_data.get("search_term_used", "")
    }