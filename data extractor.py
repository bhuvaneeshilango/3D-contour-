import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="2D Spectra Extractor", layout="wide")

st.title("2D Spectra Extractor & Arranger")
st.write("Upload raw TXT files from the Hitachi F-4500. This tool strips the metadata and neatly arranges the Wavelength and Intensity columns for immediate OriginLab plotting.")

# 1. File Uploader
uploaded_files = st.file_uploader("Upload raw 2D .TXT files", type=['txt', 'TXT'], accept_multiple_files=True)

# 2. Arrangement Mode
st.sidebar.header("Data Arrangement")
st.sidebar.write("How should the X-axis (Wavelength) be formatted?")
mode = st.sidebar.radio("Select Layout:", [
    "Titration Mode (Common X-axis, Multiple Y columns)",
    "Independent Mode (Separate X and Y for every file)"
])

if uploaded_files:
    if st.button("Extract and Arrange Data", type="primary"):
        
        parsed_data_frames = []
        
        for file in uploaded_files:
            content = file.getvalue().decode("utf-8").splitlines()
            
            data_start_idx = None
            
            # Find where the actual numeric data starts
            for i, line in enumerate(content):
                if "Data Points" in line:
                    data_start_idx = i + 2
                    break
            
            if data_start_idx is None:
                st.warning(f"Could not find data points in {file.name}. Skipping.")
                continue
                
            x_vals = []
            y_vals = []
            
            # Extract the raw numbers
            for line in content[data_start_idx:]:
                if not line.strip():
                    break  # Stop at empty lines or peak tables
                
                parts = line.strip().split()
                if len(parts) == 2:
                    try:
                        x_vals.append(float(parts[0]))
                        y_vals.append(float(parts[1]))
                    except ValueError:
                        continue
            
            # Store the extracted data based on the selected mode
            if mode == "Titration Mode (Common X-axis, Multiple Y columns)":
                # Create a dataframe with Wavelength as the index
                df = pd.DataFrame({"Wavelength_nm": x_vals, file.name: y_vals})
                df.set_index("Wavelength_nm", inplace=True)
                parsed_data_frames.append(df)
                
            else:
                # Create independent X and Y columns
                col_name_x = f"{file.name}_X"
                col_name_y = f"{file.name}_Y"
                df = pd.DataFrame({col_name_x: x_vals, col_name_y: y_vals})
                parsed_data_frames.append(df)

        # 3. Merge and Display
        if parsed_data_frames:
            if mode == "Titration Mode (Common X-axis, Multiple Y columns)":
                # Concatenate along the index (Wavelength), ensuring alignment even if lengths slightly differ
                final_df = pd.concat(parsed_data_frames, axis=1)
                final_df.sort_index(inplace=True)
                final_df.reset_index(inplace=True) # Bring Wavelength back as a regular column
            else:
                # Concatenate side-by-side horizontally
                final_df = pd.concat(parsed_data_frames, axis=1)

            st.success("Data successfully extracted and arranged!")
            
            st.write("### Data Preview")
            st.dataframe(final_df.head(10)) # Show a preview of the first 10 rows
            
            # Generate Downloadable File
            csv_buffer = io.StringIO()
            final_df.to_csv(csv_buffer, sep="\t", index=False)
            
            st.download_button(
                label="📥 Download Formatted Data (.txt)",
                data=csv_buffer.getvalue(),
                file_name="Cleaned_2D_Spectra.txt",
                mime="text/plain"
            )
        else:
            st.error("No valid data could be extracted from the uploaded files.")
