import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf

def intraday_scanner():
    # Get NSE gainers (you can modify for other criteria)
    url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    data = response.json()
    
    # Filter stocks with volume > threshold
    filtered = [stock for stock in data['data'] if stock['quantityTraded'] > 500000]
    
    # Convert to DataFrame
    df = pd.DataFrame(filtered)
    df = df[['symbol', 'openPrice', 'highPrice', 'lowPrice', 'lastPrice', 'quantityTraded']]
    
    return df.sort_values('quantityTraded', ascending=False)

print(intraday_scanner());
