import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="2D Spectra Extractor", layout="wide")

st.title("2D Spectra Extractor & Corrector")
st.write("Upload raw TXT files. This tool strips metadata, applies optional UV corrections, and neatly arranges the data for OriginLab.")

# 1. File Uploader
uploaded_files = st.file_uploader("Upload raw 2D .TXT files", type=['txt', 'TXT'], accept_multiple_files=True)

# 2. Sidebar Settings
st.sidebar.header("1. Data Arrangement")
mode = st.sidebar.radio("Select Layout:", [
    "Independent Mode (Separate X and Y for every file)",
    "Titration Mode (Common X-axis, Multiple Y columns)"
])

st.sidebar.header("2. UV Absorbance Correction")
apply_correction = st.sidebar.checkbox("Apply IFE Correction: I / (1 - 10^-A)")

uv_dict = {}
if apply_correction:
    st.sidebar.write("Paste your UV-Vis dataset (Wavelength and Absorbance):")
    uv_input = st.sidebar.text_area("Example:\n300  0.12\n310  0.15", height=200)
    
    if uv_input:
        for line in uv_input.strip().split('\n'):
            parts = line.replace(',', ' ').split()
            if len(parts) >= 2:
                try:
                    wl = float(parts[0])
                    abs_val = float(parts[1])
                    uv_dict[round(wl)] = abs_val
                except ValueError:
                    continue 

# 3. Processing Logic
if uploaded_files:
    if st.button("Extract, Correct & Arrange", type="primary"):
        
        parsed_data_frames = []
        summary_data = []
        
        for file in uploaded_files:
            content = file.getvalue().decode("utf-8").splitlines()
            
            data_start_idx = None
            ex_wl = None
            
            # Find EX WL and Data Start
            for i, line in enumerate(content):
                if "EX WL:" in line:
                    ex_wl = float(line.split(":")[1].replace("nm", "").strip())
                if "Data Points" in line:
                    data_start_idx = i + 2
                    break
            
            if data_start_idx is None:
                st.warning(f"Could not find data points in {file.name}. Skipping.")
                continue
                
            x_vals = []
            y_vals = []
            
            # Extract raw numbers
            for line in content[data_start_idx:]:
                if not line.strip(): break  
                parts = line.strip().split()
                if len(parts) == 2:
                    try:
                        x_vals.append(float(parts[0]))
                        y_vals.append(float(parts[1]))
                    except ValueError:
                        continue
            
            # Apply Correction Strategy
            correction_applied = "No"
            if apply_correction and ex_wl is not None:
                lookup_ex = round(ex_wl)
                if lookup_ex in uv_dict:
                    A = uv_dict[lookup_ex]
                    # Apply the division math to all Y values
                    y_vals = [y / (1 - 10**(-A)) for y in y_vals]
                    correction_applied = f"Yes (A={A})"
                else:
                    correction_applied = "Missing UV Data"
            
            # Create a smart name based on Excitation Wavelength (e.g., "300")
            name_prefix = str(round(ex_wl)) if ex_wl is not None else file.name.replace(".TXT", "")
            
            # Arrange Data Strategy
            if mode == "Titration Mode (Common X-axis, Multiple Y columns)":
                df = pd.DataFrame({"Wavelength_nm": x_vals, name_prefix: y_vals})
                df.set_index("Wavelength_nm", inplace=True)
                parsed_data_frames.append(df)
            else:
                col_name_x = f"{name_prefix}_X"
                col_name_y = f"{name_prefix}_Y"
                df = pd.DataFrame({col_name_x: x_vals, col_name_y: y_vals})
                parsed_data_frames.append(df)
                
            summary_data.append({"File": file.name, "Extracted Ex WL": ex_wl, "Correction": correction_applied})

        # 4. Merge and Display
        if parsed_data_frames:
            if mode == "Titration Mode (Common X-axis, Multiple Y columns)":
                final_df = pd.concat(parsed_data_frames, axis=1)
                final_df.sort_index(inplace=True)
                final_df.reset_index(inplace=True) 
            else:
                final_df = pd.concat(parsed_data_frames, axis=1)

            st.success("Data extracted, corrected, and arranged!")
            st.dataframe(pd.DataFrame(summary_data))
            
            st.write("### Data Preview")
            st.dataframe(final_df.head(5)) 
            
            csv_buffer = io.StringIO()
            final_df.to_csv(csv_buffer, sep="\t", index=False)
            
            st.download_button(
                label="📥 Download Ready-to-Plot Data (.txt)",
                data=csv_buffer.getvalue(),
                file_name="Corrected_2D_Spectra.txt",
                mime="text/plain"
            )
