# -*- coding: utf-8 -*-
"""app.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1WFoJWbiAZ_VpgI4qktn6T20hO04dcgOH
"""

import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from tqdm import tqdm
import time
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows


def process_and_save_file(source_file):
    # Read data from the 'Vehs' and 'Cas' sheets of the source file
    vehs_df = pd.read_excel(source_file, sheet_name='Vehs')
    cas_df = pd.read_excel(source_file, sheet_name='Cas')

    # Process 'Vehs' sheet
    vehs_user_df = vehs_df[['police_ref', 'veh_ref', 'Type', 'DrvSex', 'drvage']]

    # Process 'Cas' sheet for "3. Pedestrian"
    cas_pedestrians_df = cas_df[cas_df['Class'] == '3. Pedestrian']

    # Create a new DataFrame for 'Cas' data with the same columns as 'Vehs'
    cas_user_df = pd.DataFrame(columns=vehs_user_df.columns)
    cas_user_df['police_ref'] = cas_pedestrians_df['police_ref']
    cas_user_df['veh_ref'] = cas_pedestrians_df['cas_ref']
    cas_user_df['Type'] = cas_pedestrians_df['Class']
    cas_user_df['DrvSex'] = cas_pedestrians_df['Sex']
    cas_user_df['drvage'] = cas_pedestrians_df['age']

    # Concatenate 'Cas' data to 'Vehs' data
    user_df = pd.concat([vehs_user_df, cas_user_df], ignore_index=True)

    # Rename columns in user_df at the end
    user_df.rename(columns={'Type': 'Class', 'veh_ref': 'cas_ref', 'DrvSex': 'Sex', 'drvage': 'age'}, inplace=True)

    # Process for CF tab
    # Read 'Accs' sheet
    accs_df = pd.read_excel(source_file, sheet_name='Accs')

    # Create a new DataFrame to avoid SettingWithCopyWarning
    cf_df = accs_df.copy()

    # Rename 'date' column to 'Date'
    cf_df.rename(columns={'date': 'Date'}, inplace=True)

    # Identify columns for CONF and corresponding CF columns
    conf_columns = [col for col in cf_df.columns if 'CONF' in col]
    cf_columns = [col for col in cf_df.columns if 'CF' in col]
    vcu_columns = [col for col in cf_df.columns if 'VCU' in col and col != 'vcuref1']

    # Initialize an empty DataFrame to store the reshaped data
    reshaped_cf_df = pd.DataFrame()

    # Iterate over the CF, CONF, and VCU columns (excluding vcuref1) and reshape data
    for cf_col, conf_col, vcu_col in zip(cf_columns, conf_columns, vcu_columns):
        temp_df = cf_df[['police_ref', 'Date', cf_col, conf_col, vcu_col, 'vcuref1']]
        temp_df.rename(columns={cf_col: 'CF1', conf_col: 'CONF1', vcu_col: 'VCU1'}, inplace=True)
        reshaped_cf_df = pd.concat([reshaped_cf_df, temp_df])

    # Delete 'Not Coded' rows from 'CF1' and sort
    reshaped_cf_df = reshaped_cf_df[reshaped_cf_df['CF1'] != '. Not coded']
    reshaped_cf_df.sort_values(by=['police_ref', 'Date', 'CF1', 'CONF1', 'VCU1', 'vcuref1'], inplace=True)

    # Save the processed data to the same Excel file in different sheets
    with pd.ExcelWriter(source_file, engine='openpyxl', mode='a') as writer:
        user_df.to_excel(writer, sheet_name='User', index=False)
        reshaped_cf_df.to_excel(writer, sheet_name='CF', index=False)

    return user_df, reshaped_cf_df


def append_data(source_file, target_file):
    with pd.ExcelFile(target_file) as xls:  # Changed from source_df to target_file
        sheet_names = xls.sheet_names

    appended_data = {}
    for sheet_name in sheet_names:
        df_source = pd.read_excel(source_file, sheet_name=sheet_name)
        df_target = pd.read_excel(target_file, sheet_name=sheet_name)
        df_combined = pd.concat([df_source, df_target], ignore_index=True)
        appended_data[sheet_name] = df_combined

    return appended_data


def to_excel(df):
    output = BytesIO()
    workbook = Workbook()

    for sheet_name, data in df.items():
        sheet = workbook.create_sheet(title=sheet_name)
        for record in dataframe_to_rows(data, index=False, header=True):
            sheet.append(record)

    workbook.save(output)

    processed_data = output.getvalue()
    return processed_data


def get_table_download_link(df):
    val = to_excel(df)
    b64 = base64.b64encode(val).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="AccsMap_data.xlsx">Download Excel file</a>'
    return href


st.title('Excel Data Processing App for Power BI')

st.subheader('Step 1: Process Source Excel File')
source_file = st.file_uploader('Upload the source Excel file - YTD file', type=['xlsx'])

if source_file:
    user_df, reshaped_cf_df = process_and_save_file(source_file)

    source_data = {'User': user_df, 'CF': reshaped_cf_df}

    st.success('Source file processed now move to Step 2.')

st.subheader('Step 2: Append Data from Two Excel Files')
target_file = st.file_uploader('Upload the target Excel file - pre file', type=['xlsx'])

if source_file and target_file:
    st.success('Data processing started. Please wait...')

    # Use st.empty() to create a placeholder for the progress bar
    progress_bar = st.progress(0.0)

    appended_data = {}
    sheets = pd.read_excel(source_file, sheet_name=None)
    num_sheets = len(sheets)
    progress_increment = 1 / num_sheets  # Use a fractional value

    current_progress = 0.0  # Initialize progress to 0.0

    for sheet_name, df_source in tqdm(sheets.items(), desc="Processing sheets", unit="sheet"):
        df_target = pd.read_excel(target_file, sheet_name=sheet_name)
        df_combined = pd.concat([df_source, df_target], ignore_index=True)
        appended_data[sheet_name] = df_combined
        time.sleep(0.1)  # Simulate some work (you can remove this line in a real app)

        current_progress += progress_increment  # Update progress value
        progress_bar.progress(current_progress)  # Update the progress bar

    # Clear the progress bar when done
    progress_bar.empty()

    st.success('Data from two Excel files combined.')

    # Add download link
    st.markdown(get_table_download_link(appended_data), unsafe_allow_html=True)