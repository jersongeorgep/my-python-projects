import os
import pandas as pd
import streamlit as st
from io import BytesIO

st.title("📁 Folder File Lister (Local & Network)")

# Input for both local and network folders
folder_path = st.text_input("Enter folder path (Local or Network)", placeholder="e.g. C:\\Users\\MyUser\\Documents or \\\\192.168.1.100\\shared\\folder")

if folder_path:
    if os.path.exists(folder_path):
        files_data = []

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, folder_path)
                try:
                    file_size = os.path.getsize(full_path)
                except:
                    file_size = None
                    files_data.append({
                        "File Name": file,
                        "Relative Path": relative_path,
                        "Full Path": full_path,
                        "Size (KB)": round(file_size / 1024, 2) if file_size else "N/A"
                    })

        if files_data:
            df = pd.DataFrame(files_data)

            st.success(f"✅ Found {len(df)} files.")
            st.dataframe(df, use_container_width=True)

            # Export to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Files')
            output.seek(0)

            st.download_button(
                label="📥 Download Excel File",
                data=output,
                file_name='file_list.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            st.warning("📂 No files found in this folder.")
    else:
        st.error("❌ The specified path does not exist or is inaccessible.")