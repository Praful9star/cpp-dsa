"""
tools/finance.py — Crypto prices (CoinGecko) and stock prices (Yahoo Finance).

"Bitcoin price" / "How much is ETH"
"Apple stock" / "What's Tesla at"
"Market summary"
"""

import requests
import re

COIN_MAP = {
    "bitcoin": "bitcoin",   "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "solana": "solana",     "sol": "solana",
    "cardano": "cardano",   "ada": "cardano",
    "ripple": "ripple",     "xrp": "ripple",
    "polygon": "matic-network", "matic": "matic-network",
    "binance coin": "binancecoin", "bnb": "binancecoin",
    "shiba inu": "shiba-inu", "shib": "shiba-inu",
    "litecoin": "litecoin", "ltc": "litecoin",
    "polkadot": "polkadot", "dot": "polkadot",
    "chainlink": "chainlink", "link": "chainlink",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "tron": "tron",         "trx": "tron",
    "pepe": "pepe",
}

STOCK_MAP = {
    "apple": "AAPL",    "google": "GOOGL",  "alphabet": "GOOGL",
    "microsoft": "MSFT","amazon": "AMZN",   "tesla": "TSLA",
    "meta": "META",     "facebook": "META", "netflix": "NFLX",
    "nvidia": "NVDA",   "amd": "AMD",       "intel": "INTC",
    "tcs": "TCS.NS",    "tata consultancy": "TCS.NS",
    "reliance": "RELIANCE.NS", "infosys": "INFY.NS",
    "wipro": "WIPRO.NS", "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS", "sbi": "SBIN.NS",
    "sensex": "^BSESN", "nifty": "^NSEI",
    "bajaj": "BAJFINANCE.NS",
}


def get_crypto_price(query: str) -> str:
    t = query.lower()
    coin_id = next((cid for name, cid in COIN_MAP.items() if name in t), None)
    if not coin_id:
        return "Which crypto? Try: Bitcoin, Ethereum, Solana, Dogecoin..."

    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd,inr", "include_24hr_change": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get(coin_id, {})
        usd    = data.get("usd", 0)
        inr    = data.get("inr", 0)
        change = data.get("usd_24h_change", 0)
        sign   = "up" if change >= 0 else "down"
        name   = coin_id.replace("-", " ").replace("2", "").strip().title()
        return (f"{name} is ${usd:,.2f} USD — that's about ₹{inr:,.0f}. "
                f"It's {sign} {abs(change):.1f}% over the last 24 hours.")
    except Exception as e:
        return f"Couldn't get crypto price: {e}"


def get_stock_price(query: str) -> str:
    t = query.lower()
    ticker = next((sym for name, sym in STOCK_MAP.items() if name in t), None)

    if not ticker:
        m = re.search(r'\b([A-Z]{2,5})\b', query)
        ticker = m.group(1) if m else None

    if not ticker:
        return "Which stock? Try: Apple, Tesla, Reliance, Nifty, TCS..."

    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        meta  = resp.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev  = meta.get("chartPreviousClose", price) or price
        curr  = meta.get("currency", "USD")
        name  = meta.get("longName") or ticker
        pct   = ((price - prev) / prev * 100) if prev else 0
        sign  = "up" if pct >= 0 else "down"
        return (f"{name} is at {curr} {price:,.2f} — "
                f"{sign} {abs(pct):.2f}% from yesterday.")
    except Exception as e:
        return f"Couldn't get stock price: {e}"


def market_summary() -> str:
    btc   = get_crypto_price("bitcoin")
    eth   = get_crypto_price("ethereum")
    nifty = get_stock_price("nifty")
    return f"{btc} Also, {eth} And for Indian markets: {nifty}"
