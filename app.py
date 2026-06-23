import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="EEM Data Merger", layout="wide")

st.title("Fluorescence EEM Data Merger & Corrector")
st.write("Upload raw TXT files from the Hitachi F-4500. The app will extract the EX WL, apply UV corrections from your pasted data, and merge everything into an XYZ format.")

# 1. File Uploader
uploaded_files = st.file_uploader("Upload raw .TXT files", type=['txt', 'TXT'], accept_multiple_files=True)

# 2. UV Correction Settings
st.sidebar.header("UV Absorbance Correction")
apply_correction = st.sidebar.checkbox("Apply UV Correction: I / (1 - 10^-A)")

uv_dict = {}
if apply_correction:
    st.sidebar.write("Paste your entire UV-Vis dataset here (Wavelength and Absorbance columns):")
    uv_input = st.sidebar.text_area("Example:\n250  0.85\n251  0.84\n... \n500  0.12", height=300)
    
    # Parse the pasted block of data into a lookup dictionary
    if uv_input:
        for line in uv_input.strip().split('\n'):
            # Replace commas with spaces just in case it's a CSV, then split by whitespace
            parts = line.replace(',', ' ').split()
            if len(parts) >= 2:
                try:
                    wl = float(parts[0])
                    abs_val = float(parts[1])
                    # Round wavelength to nearest whole number for reliable matching
                    uv_dict[round(wl)] = abs_val
                except ValueError:
                    continue # Skip headers or text lines automatically

# 3. Processing Logic
if uploaded_files:
    if st.button("Process & Merge Data", type="primary"):
        merged_data = []
        summary_data = []

        for file in uploaded_files:
            content = file.getvalue().decode("utf-8").splitlines()
            
            ex_wl = None
            data_start_idx = None

            # Find Excitation Wavelength and Data Start
            for i, line in enumerate(content):
                if "EX WL:" in line:
                    ex_wl = float(line.split(":")[1].replace("nm", "").strip())
                if "Data Points" in line:
                    data_start_idx = i + 2
                    break
            
            if ex_wl is None:
                st.warning(f"Could not find 'EX WL:' in {file.name}. Skipping.")
                continue
                
            points_processed = 0
            correction_applied = "No"
            
            # Read the data points
            if data_start_idx is not None:
                lookup_ex = round(ex_wl)
                A = None
                
                # Check if we have an absorbance value for this excitation wavelength
                if apply_correction:
                    if lookup_ex in uv_dict:
                        A = uv_dict[lookup_ex]
                        correction_applied = f"Yes (A={A})"
                    else:
                        correction_applied = "Missing UV Data"

                for line in content[data_start_idx:]:
                    if not line.strip():
                        break # Stop at empty lines
                    
                    parts = line.strip().split()
                    if len(parts) == 2:
                        try:
                            em_wl = float(parts[0])
                            intensity = float(parts[1])
                            
                            # Apply Correction (Using Division)
                            if apply_correction and A is not None:
                                intensity = intensity / (1 - 10**(-A))
                            
                            merged_data.append([em_wl, ex_wl, intensity])
                            points_processed += 1
                        except ValueError:
                            continue
                            
            summary_data.append({
                "File": file.name, 
                "Ex WL (nm)": ex_wl, 
                "Data Points": points_processed,
                "Correction Applied": correction_applied
            })

        # 4. Display Results and Download
        if merged_data:
            st.success("Data processed successfully!")
            
            # Show Summary table
            st.write("### Processing Summary")
            st.dataframe(pd.DataFrame(summary_data))
            
            # Convert to DataFrame and sort by Excitation, then Emission
            df = pd.DataFrame(merged_data, columns=["Emission_nm", "Excitation_nm", "Intensity"])
            df = df.sort_values(by=["Excitation_nm", "Emission_nm"])
            
            # Create Download Button
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