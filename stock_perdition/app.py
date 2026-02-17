import streamlit as st
from nsepy import get_history
from datetime import date
import pandas as pd
from ta.trend import SMAIndicator
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

st.title("📊 NSE Intraday Stock Predictor")

# User input for stock symbol and date range
symbol = st.text_input("Enter NSE Stock Symbol (e.g. RELIANCE, TCS, INFY)", "RELIANCE")
start_date = st.date_input("Start Date", date(2024, 4, 1))
end_date = st.date_input("End Date", date(2024, 4, 12))

if st.button("Fetch & Predict"):
    with st.spinner('Fetching data & training model...'):
        # Fetch data
        data = get_history(symbol=symbol.upper(), start=start_date, end=end_date, index=False)

        if data.empty:
            st.error("No data found. Check symbol or date range.")
        else:
            # Feature engineering
            data['SMA_5'] = SMAIndicator(data['Close'], window=5).sma_indicator()
            data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
            data.dropna(inplace=True)

            X = data[['SMA_5']]
            y = data['Target']

            X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False, test_size=0.2)

            model = RandomForestClassifier(n_estimators=100)
            model.fit(X_train, y_train)

            predictions = model.predict(X_test)
            acc = accuracy_score(y_test, predictions)

            st.success(f"Prediction Accuracy: {acc:.2%}")

            data['Prediction'] = model.predict(X)
            st.line_chart(data[['Close', 'SMA_5']])
            st.write(data[['Close', 'SMA_5', 'Prediction']].tail())

