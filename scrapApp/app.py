import streamlit as st
import pandas as pd
from serpapi import GoogleSearch

st.title("LinkedIn CEO Scraper - Dubai 🌆")

api_key = st.text_input("Enter your SerpApi Key:", type="password")
query = st.text_input("Search Query:", value="CEO Dubai site:linkedin.com/in")

if st.button("Search") and api_key:
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    if "organic_results" in results:
        leads = []
        for result in results["organic_results"]:
            title = result.get("title")
            link = result.get("link")
            snippet = result.get("snippet", "")
            leads.append({
                "Name / Title": title,
                "LinkedIn URL": link,
                "Info": snippet
            })

        df = pd.DataFrame(leads)
        st.dataframe(df)

        # CSV Export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name='dubai_ceo_linkedin.csv',
            mime='text/csv',
        )
    else:
        st.warning("No results found or invalid API key.")
