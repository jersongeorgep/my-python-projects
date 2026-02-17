import streamlit as st
import json
from io import BytesIO

st.title("📝 JSON Aggregator and Merger Tool")
st.write("Upload multiple JSON files to combine and merge them.")

# File uploader
uploaded_files = st.file_uploader("Upload JSON files", type="json", accept_multiple_files=True)

if uploaded_files:
    combined_data = []  # Store each JSON object in a list
    merged_data = {}  # Store merged JSON

    for file in uploaded_files:
        file_data = json.load(file)
        combined_data.append(file_data)  # Add to list
        merged_data.update(file_data)  # Merge keys directly

    # Display combined JSON list
    st.subheader("Combined JSON Data (List Format)")
    st.json(combined_data)

    # Display merged JSON
    st.subheader("Merged JSON Data (Single Object)")
    st.json(merged_data)

    # Convert combined JSON list to downloadable file
    combined_json_str = json.dumps(combined_data, indent=4)
    combined_bytes = BytesIO(combined_json_str.encode())

    st.download_button(
        label="📥 Download Combined JSON (List)",
        data=combined_bytes,
        file_name="combined.json",
        mime="application/json"
    )

    # Convert merged JSON object to downloadable file
    merged_json_str = json.dumps(merged_data, indent=4)
    merged_bytes = BytesIO(merged_json_str.encode())

    st.download_button(
        label="📥 Download Merged JSON (Object)",
        data=merged_bytes,
        file_name="merged.json",
        mime="application/json"
    )
