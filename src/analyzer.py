# src/analyzer.py
import re
from typing import Dict, List, Optional

from .config import MIN_DISCOUNT_PCT, LIQUID_POKEMON


class CardParser:
    """
    Handles all raw listing title → structured metadata logic.
    Reusable for future scrapers (eBay, TCGPlayer, etc.).
    """

    POKEMON_KEYWORDS: List[str] = [p.lower() for p in LIQUID_POKEMON]

    @staticmethod
    def parse_title(title: str) -> Dict:
        t = title.lower().strip()

        # Card number
        # normalize leading zeros (#015 → 15)
        num_match = re.search(r'#([a-z0-9]+)', t)
        card_number = num_match.group(1).lstrip('0') if num_match else None
        if card_number == "":
            card_number = "0"

        # Year
        year_match = re.search(r'\b(19|20)\d{2}\b', t)
        year = year_match.group(0) if year_match else None

        # Pokemon name
        pokemon = next((p for p in CardParser.POKEMON_KEYWORDS if p in t), None)

        # Variation 
        variations = [
            "ex", "vmax", "v", "vstar", "gx", "holo", "reverse holo",
            "full art", "fullart", "radiant", "secret rare", "mega",
            "full-art", "secret-rare"
        ]
        variation = next((v for v in variations if v in t), None)

        # === ROBUST SET EXTRACTION ===
        set_name = None
        grade_match = re.search(r'(PSA|BGS|CGC|TAG)\s*\d+\.?\d*', title, re.IGNORECASE)
        if grade_match:
            pos = title.find(grade_match.group(0)) + len(grade_match.group(0))
            after = title[pos:].strip()
            after = re.sub(r'(?:\s+Pokemon.*|\s*\.\.\.|\s*$)', '', after, flags=re.IGNORECASE).strip()
            if after and len(after) > 3:
                set_name = after

        if not set_name:
            set_match = re.search(r'(?:pokemon\s+)?([\w\s&-]+?)(?:\s+pokemon)?$', t, re.IGNORECASE)
            if set_match:
                set_name = set_match.group(1).strip()

        return {
            "raw": title,
            "pokemon": pokemon,
            "card_number": card_number,
            "year": year,
            "variation": variation,
            "set": set_name
        }

    @staticmethod
    def detect_language(title: str) -> str:
        t = title.lower()
        if any(x in t for x in ["japanese", "jp"]):
            return "japanese"
        elif any(x in t for x in ["chinese", "cn"]):
            return "chinese"
        elif any(x in t for x in ["korean", "kr"]):
            return "korean"
        return "english"

    @staticmethod
    def detect_grade(title: str) -> str:
        match = re.search(r'(PSA|BGS|CGC|TAG)\s*(\d+\.?\d*)', title, re.IGNORECASE)
        if match:
            return f"{match.group(1).upper()} {match.group(2)}"
        return "Ungraded"


def analyze(listing: Dict, fair_value_data: Dict) -> Optional[Dict]:
    """Unchanged — returns arbitrage opportunity or None."""
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