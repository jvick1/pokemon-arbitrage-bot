# src/me_client.py
import time
import re
from typing import List, Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .config import LIQUID_POKEMON, SOL_PRICE

class MagicEdenClient:
    URL = "https://collectorcrypt.com/marketplace/cards"
    
    def __init__(self, headless: bool = False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        print("✅ CollectorCrypt Scraper initialized")

    def fetch_filtered_listings(self, pokemon_names: List[str] = None, scroll_times: int = 25) -> List[Dict]:
        if pokemon_names is None:
            pokemon_names = LIQUID_POKEMON

        print(f"Opening Collector Crypt... (SOL = ${SOL_PRICE})")
        self.driver.get(self.URL)
        time.sleep(8)

        print(f"Scrolling {scroll_times} times...")
        for i in range(scroll_times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

        time.sleep(5)

        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        listing_elements = soup.find_all("a", class_="link-card")

        print(f"Found {len(listing_elements)} listing cards.")

        all_listings = []
        for elem in listing_elements:
            try:
                # Title
                name_div = elem.find("div", class_="card__details__name")
                title = name_div.get_text(strip=True) if name_div else ""
                if not title:
                    continue

                if not any(poke.lower() in title.lower() for poke in pokemon_names):
                    continue

                # === IMPROVED PRICE EXTRACTION ===
                price_container = elem.find("div", class_="card__details__insurance-value")
                if not price_container:
                    continue

                price_text = price_container.get_text(strip=True)
                
                # Find the numeric value (more robust)
                price_matches = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', price_text)
                if not price_matches:
                    continue
                raw_price = float(price_matches[-1].replace(',', ''))

                # Detect currency by presence of Solana SVG
                has_sol_svg = price_container.find("svg") is not None
                currency = "SOL" if has_sol_svg else "USDC"

                # Convert to USD
                usd_price = raw_price * SOL_PRICE if currency == "SOL" else raw_price

                # Image
                img = elem.find("img", class_="nft-image")
                image_url = img.get("src", "") if img else ""

                listing_url = "https://collectorcrypt.com" + elem.get("href", "")

                listing = {
                    "title": title.strip(),
                    "currency": currency,
                    "raw_price": raw_price,
                    "usd_price": round(usd_price, 2),
                    "listing_url": listing_url,
                    "image_url": image_url,
                }
                all_listings.append(listing)
                print(f"   ✅ {currency} {raw_price} → ${usd_price:.2f} | {title[:90]}...")

            except Exception as e:
                continue

        print(f"\n✅ Finished scraping. Found {len(all_listings)} liquid listings.")
        return all_listings

    def close(self):
        try:
            self.driver.quit()
        except:
            pass
        print("✅ CollectorCrypt Scraper closed")