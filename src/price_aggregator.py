# src/price_aggregator.py
import re
import time
import urllib.parse
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None  # fallback if not installed

try:
    from src.config import LIQUID_POKEMON
except ImportError:
    LIQUID_POKEMON = [
        "charizard", "pikachu", "gyarados", "umbreon", "eevee",
        "blastoise", "venusaur", "dragonite", "lucario", "gengar",
        "arceus", "charmander", "mewtwo", "mew"
    ]


class PriceAggregator:
    def __init__(self, headless: bool = True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.pokemon_keywords = [p.lower() for p in LIQUID_POKEMON]

        print("✅ PriceAggregator initialized (refactored pipeline)")

    # =========================
    # PHASE 1 — STRUCTURED PARSER
    # =========================
    def _parse_title(self, title: str) -> Dict:
        t = title.lower().strip()

        # Card number — normalize leading zeros (#015 → 15)
        num_match = re.search(r'#([a-z0-9]+)', t)
        card_number = num_match.group(1).lstrip('0') if num_match else None
        if card_number == "":  # edge case for #000
            card_number = "0"

        # Year
        year_match = re.search(r'\b(19|20)\d{2}\b', t)
        year = year_match.group(0) if year_match else None

        # Pokemon name
        pokemon = None
        for p in self.pokemon_keywords:
            if p in t:
                pokemon = p
                break

        # Variation 
        variations = [
            "ex", "vmax", "v", "vstar", "gx", "holo", "reverse holo",
            "full art", "fullart", "radiant", "secret rare"
        ]
        variation = next((v for v in variations if v in t), None)
        set_name = None
        grade_match = re.search(r'(PSA|BGS|CGC|TAG)\s*\d+\.?\d*', title, re.IGNORECASE)
        if grade_match:
            pos = title.find(grade_match.group(0)) + len(grade_match.group(0))
            after = title[pos:].strip()
            # Clean trailing junk
            after = re.sub(r'(?:\s+Pokemon.*|\s*\.\.\.|\s*$)', '', after, flags=re.IGNORECASE).strip()
            if after and len(after) > 3:
                set_name = after

        # Fallback: last meaningful phrase
        if not set_name:
            set_match = re.search(r'(?:pokemon\s+)?([\w\s&-]+?)(?:\s+pokemon)?$', t, re.IGNORECASE)
            if set_match:
                set_name = set_match.group(1).strip()

        return {
            "raw": title,
            "pokemon": pokemon,
            "card_number": card_number,          # no leading zero
            "year": year,
            "variation": variation,
            "set": set_name
        }

    def _detect_language(self, title: str) -> str:
        t = title.lower()
        if any(x in t for x in ["japanese", "jp"]):
            return "japanese"
        elif any(x in t for x in ["chinese", "cn"]):
            return "korean"
        elif any(x in t for x in ["korean", "kr"]):
            return "korean"
        return "english"

    def _detect_grade(self, title: str) -> str:
        match = re.search(r'(PSA|BGS|CGC|TAG)\s*(\d+\.?\d*)', title, re.IGNORECASE)
        if match:
            return f"{match.group(1).upper()} {match.group(2)}"
        return "Ungraded"

    # =========================
    # PHASE 2 — QUERY BUILDER (now includes variation + #)
    # =========================
    def _build_queries(self, parsed: Dict) -> List[str]:
        queries = []
        pokemon = parsed["pokemon"]
        card = parsed["card_number"]
        var = parsed["variation"]

        # Stage 1 — BEST query
        if pokemon and card:
            base = f"{pokemon} #{card}"
            if var:
                base = f"{var} {base}"
            queries.append(base)

        # Stage 2 — with set 
        if parsed["set"] and pokemon and card:
            queries.append(f"{pokemon} {parsed['set']} #{card}")

        # Final fallback
        queries.append(parsed["raw"][:80])

        return list(dict.fromkeys(queries))  # dedupe

    def _fetch_results(self, query: str):
        url = f"https://www.pricecharting.com/search-products?q={urllib.parse.quote(query)}&type=prices"
        self.driver.get(url)
        time.sleep(2.5)
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        return soup.find_all("tr", id=lambda x: x and x.startswith("product-"))

    # =========================
    # PHASE 3 — SCORING ENGINE 
    # =========================
    def _score_row(self, row, parsed: Dict, language: str) -> float:
        title_cell = row.find("td", class_="title")
        if not title_cell:
            return -999

        row_title = title_cell.get_text(strip=True).lower()
        score = 0

        # Core matches
        if parsed["pokemon"] and parsed["pokemon"] in row_title:
            score += 20
        if parsed["card_number"] and parsed["card_number"].lower() in row_title:
            score += 40

        # Set column extraction from PriceCharting
        set_cell = (row.find("td", class_="set") or
                    row.find("td", class_="console") or
                    row.find("a", href=re.compile(r'/pokemon-|/console/pokemon-')))
        row_set = set_cell.get_text(strip=True).lower() if set_cell else ""

        if parsed["set"]:
            if parsed["set"].lower() in row_title or parsed["set"].lower() in row_set:
                score += 25
            elif fuzz:
                ratio = fuzz.partial_ratio(parsed["set"].lower(), row_set)
                score += int(ratio * 0.25)

        # Variation
        if parsed["variation"] and parsed["variation"] in row_title:
            score += 10

        # Language
        if language == "english" and "japanese" not in row_title:
            score += 8
        elif language == "japanese" and "japanese" in row_title:
            score += 15

        # Fuzzy boost
        if fuzz:
            score += fuzz.partial_ratio(parsed["raw"].lower(), row_title) * 0.15

        # Tiny year bonus
        if parsed.get("year") and parsed["year"] in row_title:
            score += 5

        return score

    # =========================
    # MAIN PIPELINE
    # =========================
    def get_fair_value(self, listing_title: str) -> Optional[Dict]:
        parsed = self._parse_title(listing_title)
        grade = self._detect_grade(listing_title)
        language = self._detect_language(listing_title)

        # Clean print exactly as you wanted
        card_display = f"#{parsed['card_number']}" if parsed["card_number"] else "None"
        print(f"Parsed → Pokemon: {parsed['pokemon']} | {card_display} | "
              f"Set: {parsed['set']} | Var: {parsed['variation']}"
              f"Grade: {grade} | Language: {language}")

        queries = self._build_queries(parsed)

        best_row = None
        best_score = -999

        for query in queries:
            print(f"   🔎 Trying query: {query}")
            rows = self._fetch_results(query)

            for row in rows:
                score = self._score_row(row, parsed, language)
                if score > best_score:
                    best_score = score
                    best_row = row

            if best_score >= 60:  # early exit on strong match
                break

        if not best_row:
            print("   ⚠️ No match found")
            return None

        price = self._extract_grade_price(best_row, grade)

        return {
            "average_usd": round(price, 2),
            "sources": ["PriceCharting"],
            "grade_detected": grade,
            "confidence": round(min(0.7 + (best_score / 100), 0.95), 2),
            "matched_card": best_row.find("td", class_="title").get_text(strip=True),
            "pricecharting_link": best_row.find("a")["href"],
            "search_term_used": queries[0],
            "language_detected": language
        }

    # =========================
    # PRICE EXTRACTION
    # =========================
    def _extract_grade_price(self, row, detected_grade: str) -> float:
        grade_map = {
            "PSA 10": "manual_only_price",
            "CGC 10": "manual_only_price",
            "PSA 9": "graded_price",
            "CGC 9.5": "graded_price",
            "CGC 9": "graded_price",
            "PSA 8": "used_price",
        }
        col_id = grade_map.get(detected_grade, "used_price")

        price_cell = row.find("td", id=col_id)
        if price_cell:
            match = re.search(r'[\d.,]+', price_cell.get_text())
            if match:
                return float(match.group(0).replace(',', ''))

        for td in row.find_all("td", class_="price"):
            match = re.search(r'[\d.,]+', td.get_text())
            if match:
                return float(match.group(0).replace(',', ''))

        return 0.0

    def close(self):
        try:
            self.driver.quit()
        except:
            pass
        print("✅ PriceAggregator closed")