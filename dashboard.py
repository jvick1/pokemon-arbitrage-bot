'''
Run with -> streamlit run dashboard.py
'''


# dashboard.py
import streamlit as st
import pandas as pd
import webbrowser

# Import config for thresholds
try:
    from src.config import (
        MIN_DISCOUNT_PCT,
        STRONG_DEAL_THRESHOLD,
        GOOD_DEAL_THRESHOLD,
        SOL_PRICE
    )
except ImportError:
    MIN_DISCOUNT_PCT = 20.0
    STRONG_DEAL_THRESHOLD = 25.0
    GOOD_DEAL_THRESHOLD = 15.0
    SOL_PRICE = 82.01

st.set_page_config(page_title="Liquid Pokémon Arbitrage", layout="wide")
st.title("🃏 Liquid Pokémon Arbitrage Scanner (MVP)")

CSV_ARBITRAGE = "arbitrage_opportunities.csv"
CSV_ALL = "all_listings.csv"

# -----------------------------
# 🔄 RUN FRESH SCAN
# -----------------------------
if st.button("🔄 Run Fresh Scan"):
    with st.spinner("Scanning Collector Crypt + analyzing with Pokéllector..."):
        try:
            from run_bot import main
            main()
            st.success("✅ Scan completed!")
            st.rerun()
        except Exception as e:
            st.error(f"Scan failed: {e}")

# Helper function to display a card row (no 'self')
def display_card_row(row: pd.Series, is_arbitrage: bool = False):
    col1, col2, col3 = st.columns([1.3, 4.0, 1.4])

    with col1:
        img_url = row.get("image_url", "")
        if pd.notna(img_url) and str(img_url).startswith("http"):
            st.image(img_url, width=170)
        else:
            st.write("📷 No image")

    with col2:
        title = row.get("title", "Unknown Card")
        st.markdown(f"**{title}**")

        usd_price = float(row.get("usd_price", row.get("me_price", 0)) or 0)
        raw_price = float(row.get("raw_price", usd_price) or 0)
        currency = row.get("currency", "SOL")

        fair_value = float(row.get("fair_value", 0) or 0)
        discount = float(row.get("discount_pct", 0) or 0)

        # Metrics
        st.metric(
            label="Listed on Collector Crypt",
            value=f"${usd_price:.2f} USD",
            delta=f"{raw_price:.2f} {currency}"
        )

        st.metric(
            label="Pokéllector Fair Value",
            value=f"${fair_value:.2f}",
            delta=f"{discount:.1f}% below"
        )

        # Deal Strength Tag (shown in both tabs)
        if discount >= STRONG_DEAL_THRESHOLD:
            st.success("🔥 STRONG DEAL")
        elif discount >= GOOD_DEAL_THRESHOLD:
            st.info("👍 Good Deal")

        # Metadata
        st.caption(
            f"**Grade:** {row.get('grade', 'N/A')} | "
            f"**Sources:** {row.get('sources', 'Pokéllector')} | "
            f"**Confidence:** {float(row.get('confidence', 0) or 0):.2f}"
        )

        # Links
        listing_url = row.get("listing_url", "")
        pc_link = row.get("pricecharting_link", "")

        if listing_url and str(listing_url).startswith("http"):
            st.markdown(f"[🔗 Collector Crypt Listing]({listing_url})")
        if pc_link and str(pc_link).startswith("http"):
            st.markdown(f"[📊 PriceCharting Search]({pc_link})")

    with col3:
        if listing_url and st.button("✅ Open Listing", key=f"open_{is_arbitrage}_{row.name}"):
            webbrowser.open(listing_url)
            st.toast("Opened listing in browser", icon="✅")

        if pc_link and st.button("📊 PriceCharting", key=f"pc_{is_arbitrage}_{row.name}"):
            webbrowser.open(pc_link)
            st.toast("Opened PriceCharting", icon="📈")

        if st.button("❌ Skip", key=f"skip_{is_arbitrage}_{row.name}"):
            st.info("Skipped this card")

    st.divider()

# -----------------------------
# TABS
# -----------------------------
tab1, tab2 = st.tabs(["🔥 Arbitrage Opportunities", "📋 All Listings"])

with tab1:
    try:
        df_arb = pd.read_csv(CSV_ARBITRAGE)
        st.subheader(f"🔥 Arbitrage Opportunities ({len(df_arb)} found)")

        for idx, row in df_arb.iterrows():
            display_card_row(row, is_arbitrage=True)

    except FileNotFoundError:
        st.info("No arbitrage opportunities found yet. Run a scan!")

with tab2:
    try:
        df_all = pd.read_csv(CSV_ALL)
        st.subheader(f"All Liquid Listings ({len(df_all)} found)")

        for idx, row in df_all.iterrows():
            display_card_row(row, is_arbitrage=False)

    except FileNotFoundError:
        st.info("No listings scanned yet. Run a scan first.")

# -----------------------------
# RAW DATA VIEW
# -----------------------------
with st.expander("📋 View Raw Data Tables"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Arbitrage Opportunities CSV**")
        try:
            st.dataframe(pd.read_csv(CSV_ARBITRAGE), use_container_width=True)
        except:
            st.write("No arbitrage file yet.")
    with col_b:
        st.write("**All Listings CSV**")
        try:
            st.dataframe(pd.read_csv(CSV_ALL), use_container_width=True)
        except:
            st.write("No all_listings file yet.")

# Footer
st.caption(f"SOL Price: ${SOL_PRICE} | Min Discount: {MIN_DISCOUNT_PCT}% | "
           f"Strong Deal: ≥{STRONG_DEAL_THRESHOLD}% | Good Deal: ≥{GOOD_DEAL_THRESHOLD}%")