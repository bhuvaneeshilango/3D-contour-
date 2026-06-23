import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="EEM Data Merger", layout="wide")

st.title("Fluorescence EEM Data Merger & Corrector")
st.write("Upload raw TXT files from the Hitachi F-4500. Extract data, remove scattering, apply UV corrections, and normalize for 3D contour plotting.")

# 1. File Uploader
uploaded_files = st.file_uploader("Upload raw .TXT files", type=['txt', 'TXT'], accept_multiple_files=True)

# 2. Sidebar Controls
st.sidebar.header("1. Scattering Removal")
st.sidebar.write("Crop data to avoid 2nd order scattering peaks.")
# This allows you to change the cutoff from 10nm to 20nm instantly for ACN
end_margin = st.sidebar.number_input("Stop Emission at (2 * Ex) minus [X] nm:", value=10, step=5)

st.sidebar.header("2. UV Absorbance Correction")
apply_correction = st.sidebar.checkbox("Apply IFE Correction: I / (1 - 10^-A)")

uv_dict = {}
if apply_correction:
    st.sidebar.write("Paste your UV-Vis dataset (Wavelength and Absorbance):")
    uv_input = st.sidebar.text_area("Example:\n250  0.85\n251  0.84", height=200)
    
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

st.sidebar.header("3. Normalization")
st.sidebar.write("Scale the Z-axis so the maximum intensity equals 1.")
normalize_data = st.sidebar.checkbox("Normalize Matrix (Global 0 to 1)")

# 3. Processing Logic
if uploaded_files:
    if st.button("Process & Merge Data", type="primary"):
        merged_data = []
        summary_data = []

        for file in uploaded_files:
            content = file.getvalue().decode("utf-8").splitlines()
            ex_wl = None
            data_start_idx = None

            # Find Excitation Wavelength
            for i, line in enumerate(content):
                if "EX WL:" in line:
                    ex_wl = float(line.split(":")[1].replace("nm", "").strip())
                if "Data Points" in line:
                    data_start_idx = i + 2
                    break
            
            if ex_wl is None:
                continue
                
            points_processed = 0
            correction_applied = "No"
            
            if data_start_idx is not None:
                lookup_ex = round(ex_wl)
                A = None
                
                if apply_correction:
                    if lookup_ex in uv_dict:
                        A = uv_dict[lookup_ex]
                        correction_applied = f"Yes (A={A})"
                    else:
                        correction_applied = "Missing UV Data"

                # Define the mathematical cutoff point for this specific file
                cutoff_wavelength = (2 * ex_wl) - end_margin

                for line in content[data_start_idx:]:
                    if not line.strip():
                        break 
                    
                    parts = line.strip().split()
                    if len(parts) == 2:
                        try:
                            em_wl = float(parts[0])
                            intensity = float(parts[1])
                            
                            # STEP A: Apply the Scattering Crop
                            if em_wl > cutoff_wavelength:
                                continue # Skip this data point entirely
                            
                            # STEP B: Apply IFE Correction
                            if apply_correction and A is not None:
                                intensity = intensity / (1 - 10**(-A))
                            
                            merged_data.append([em_wl, ex_wl, intensity])
                            points_processed += 1
                        except ValueError:
                            continue
                            
            summary_data.append({
                "File": file.name, 
                "Ex WL (nm)": ex_wl, 
                "Points Kept": points_processed,
                "Correction": correction_applied
            })

        # STEP C: Apply Global Normalization
        if merged_data and normalize_data:
            # Find the absolute highest intensity in the entire dataset
            max_intensity = max(row[2] for row in merged_data)
            if max_intensity > 0:
                # Divide every intensity by the maximum
                for row in merged_data:
                    row[2] = row[2] / max_intensity

        # 4. Display Results
        if merged_data:
            st.success("Data processed successfully!")
            
            st.write("### Processing Summary")
            st.dataframe(pd.DataFrame(summary_data))
            
            df = pd.DataFrame(merged_data, columns=["Emission_nm", "Excitation_nm", "Intensity"])
            df = df.sort_values(by=["Excitation_nm", "Emission_nm"])
            
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, sep="\t", index=False)
            
            st.download_button(
                label="📥 Download Merged Data (XYZ format)",
                data=csv_buffer.getvalue(),
                file_name="Merged_EEM_Data.txt",
                mime="text/plain"
            )
        else:
            st.error("No valid data points could be extracted.")
