# src/price_aggregator.py
import time
import urllib.parse
from typing import Dict, List, Optional
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

from .analyzer import CardParser


class PriceAggregator:
    """
    Optimized PriceCharting scraper & matcher.
    Now much leaner — parsing lives in analyzer.CardParser.
    """

    def __init__(self, headless: bool = True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=chrome_options)
        print("✅ PriceAggregator initialized (optimized v3 — parser moved to analyzer)")

    # =========================
    # PHASE 2 — QUERY BUILDER
    # =========================
    def _build_queries(self, parsed: Dict) -> List[str]:
        queries: List[str] = []
        pokemon = parsed["pokemon"]
        card = parsed["card_number"]
        var = parsed["variation"]
        set_name = parsed["set"]
        year = parsed["year"]

        if not pokemon or not card:
            queries.append(parsed["raw"][:80])
            return queries

        # 1. Best exact format
        base = f"{pokemon} #{card}"
        if var:
            queries.append(f"{var} {base}")
        queries.append(base)

        # 2. Without #
        if var:
            queries.append(f"{var} {pokemon} {card}")
        queries.append(f"{pokemon} {card}")

        # 3. With set
        if set_name:
            queries.append(f"{pokemon} {set_name} #{card}")
            queries.append(f"{pokemon} {set_name} {card}")

        # 4. With year (great for duplicate card numbers)
        if year:
            queries.append(f"{pokemon} {year} {card}")

        # 5. Raw fallback
        queries.append(parsed["raw"][:80])

        return list(dict.fromkeys(queries))

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
            return -999.0

        row_title = title_cell.get_text(strip=True).lower()
        score = 0.0

        if parsed["pokemon"] and parsed["pokemon"] in row_title:
            score += 20
        if parsed["card_number"] and parsed["card_number"].lower() in row_title:
            score += 40

        # Bonus for exact card number format
        card_num = parsed["card_number"]
        if card_num and (f"#{card_num}" in row_title or f" {card_num} " in f" {row_title} "):
            score += 12

        # Set column from PriceCharting
        set_cell = (row.find("td", class_="set") or
                    row.find("td", class_="console") or
                    row.find("a", href=re.compile(r'/pokemon-|/console/pokemon-')))
        row_set = set_cell.get_text(strip=True).lower() if set_cell else ""

        if parsed["set"]:
            set_lower = parsed["set"].lower()
            if set_lower in row_title or set_lower in row_set:
                score += 25
            elif fuzz:
                ratio = fuzz.partial_ratio(set_lower, row_set)
                score += int(ratio * 0.3)

        if parsed["variation"] and parsed["variation"] in row_title:
            score += 12

        # Language
        if language == "english" and "japanese" not in row_title:
            score += 8
        elif language == "japanese" and "japanese" in row_title:
            score += 18
        elif language in ("chinese", "korean") and language in row_title:
            score += 15

        if fuzz:
            score += fuzz.partial_ratio(parsed["raw"].lower(), row_title) * 0.22

        if parsed.get("year") and parsed["year"] in row_title:
            score += 6

        return score

    # =========================
    # MAIN PIPELINE 
    # =========================
    def get_fair_value(self, listing_title: str) -> Optional[Dict]:
        parsed = CardParser.parse_title(listing_title)
        grade = CardParser.detect_grade(listing_title)
        language = CardParser.detect_language(listing_title)

        print(f"🔍 Parsed → Pokemon: {parsed['pokemon']} | #{parsed['card_number'] or 'None'} | "
              f"Set: {parsed['set'] or 'None'} | Var: {parsed['variation'] or 'None'} | "
              f"Grade: {grade} | Language: {language}")

        queries = self._build_queries(parsed)

        best_row = None
        best_score = -999.0

        for query in queries:
            print(f"   🔎 Trying query: {query}")
            rows = self._fetch_results(query)

            for row in rows:
                score = self._score_row(row, parsed, language)
                if score > best_score:
                    best_score = score
                    best_row = row

            if best_score >= 65:
                break

        if not best_row:
            print("   ⚠️ No match found")
            return None

        price = self._extract_grade_price(best_row, grade)

        return {
            "average_usd": round(price, 2),
            "sources": ["PriceCharting"],
            "grade_detected": grade,
            "confidence": round(min(0.75 + (best_score / 100), 0.98), 2),
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