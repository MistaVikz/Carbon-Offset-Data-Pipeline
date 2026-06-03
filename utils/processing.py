import pandas as pd

def load_project_data(filename, type, sheet='Sheet1', skip = 0, encode='utf-8'):
    """
    Load project metadata from either a CSV or Excel file in the project data folder.

    Parameters
    ----------
    filename : str
        The name of the file to load, relative to `project data/`.
    type : str
        File type, either `"Excel"` or `"CSV"`.
    sheet : str, optional
        Excel sheet name to read when `type == "Excel"`. Defaults to `'Sheet1'`.
    skip : int, optional
        Number of rows to skip when reading an Excel sheet. Defaults to `0`.
    encode : str, optional
        Text encoding to use when reading CSV files. Defaults to `'utf-8'`.

    Returns
    -------
    pandas.DataFrame
        The loaded project data.
    """
    if type == "Excel":
        try:
            proj_df = pd.read_excel(f'project data\\{filename}', sheet_name=sheet, skiprows=skip)
        except FileNotFoundError:
            print(f"Error: '{filename}' not found in the project data folder.")    
    else:
        try:
            proj_df = pd.read_csv(f'project data\\{filename}', encoding=encode)
        except FileNotFoundError:
            print(f"Error: '{filename}' not found in the data folder.")    
    return proj_df

def process_credits_data(credits_df, registry_code):
    """
    Process raw credits transactions for a given registry and return per-project totals.

    Parameters
    - credits_df (pd.DataFrame): Raw credits transactions. Expected columns include:
        'project_id', 'transaction_type', 'registry_code', 'vintage', 'quantity'.
    - registry_code (str): Registry code to filter by (e.g., 'VCS').

    Returns
    - pd.DataFrame: Summary per project with columns:
        - 'numeric_id' (Int64): numeric project ID extracted from 'project_id'
        - 'Actual Emission Reductions' (numeric): net sum of quantities (issuances minus cancellations)
        - 'Num Years' (int): count of distinct vintage years used to compute the total

    Notes
    - Rows with 'transaction_type' == 'cancellation' are converted to negative quantities
      before aggregation so cancellations reduce the net total.
    """
    # Extract registry code and numeric ID from project_id
    credits_df[['registry_code', 'numeric_id']] = credits_df['project_id'] \
        .astype(str) \
        .str.extract(r'([A-Za-z]+)[\s\-]*(\d+)', expand=True)
    credits_df['numeric_id'] = credits_df['numeric_id'].astype(float).astype('Int64')

    # Filter for issued/cancelled credits and registry code
    credits_df = credits_df[credits_df['transaction_type'].isin(['issuance', 'cancellation'])]
    credits_df = credits_df[credits_df['registry_code'] == registry_code]

    # Set cancelled quantities to negative
    credits_df.loc[credits_df['transaction_type'] == 'cancellation', 'quantity'] = \
        -credits_df.loc[credits_df['transaction_type'] == 'cancellation', 'quantity']

    # Calculate total issued credits for each project by vintage
    issued_by_vintage = credits_df.groupby(['numeric_id', 'vintage'])['quantity'].sum().reset_index()

    # Count distinct vintages (number of years) per project
    years_count = issued_by_vintage.groupby('numeric_id')['vintage'] \
        .nunique().reset_index(name='Num Years')

    # Sum across vintages to get Actual ERs per project
    issued_by_proj = issued_by_vintage.groupby('numeric_id')['quantity'].sum().reset_index()
    issued_by_proj.rename(columns={'quantity': 'Actual Emission Reductions'}, inplace=True)

    # Merge the Num Years column into the final result
    issued_by_proj = issued_by_proj.merge(years_count, on='numeric_id', how='left')

    return issued_by_proj

def build_merged_dataframe(proj_df, issued_df, registry_code):
    """
    Merge project metadata with issued-credit summaries and compute estimated totals.

    Parameters
    - proj_df (pd.DataFrame): Project metadata; must include 'Project ID' and
      'Estimated Annual Emission Reductions'.
    - issued_df (pd.DataFrame): Issued-credit summary; must include 'numeric_id',
      'Actual Emission Reductions', and 'Num Years'.
    - registry_code (str): Registry code to set on the merged rows.

    Returns
    - pd.DataFrame: Inner-joined DataFrame (projects with issued credits) including:
        - 'Estimated Emission Reductions' = 'Estimated Annual Emission Reductions' * 'Num Years'
        - 'registry_code' set to the provided value
    """
    # Merge dataframes to include Actual ERs (only keep projects with actual ERs)
    merged_df = pd.merge(proj_df, issued_df, left_on='Project ID', right_on='numeric_id', how='inner')
    
    # Get the Estimated ERs (Estimated Annual * Number of Years)
    merged_df['Estimated Emission Reductions'] = merged_df['Estimated Annual Emission Reductions'] * merged_df['Num Years']

    # Prepare the merged data
    merged_df.drop(columns=['numeric_id','Estimated Annual Emission Reductions', 'Num Years'], inplace=True)
    merged_df['registry_code'] = registry_code

    return merged_df

def get_CDM_total_estimated_ERs(cdm_proj_df):
    year_cols = [col for col in cdm_proj_df.columns
                 if isinstance(col, int) and 2000 <= col <= 2047]

    if not year_cols:
        raise ValueError("No CDM year columns found in the dataframe")

    cdm_proj_df = cdm_proj_df.copy()
    cdm_proj_df["Estimated Emission Reductions"] = (
        cdm_proj_df[year_cols]
        .fillna(0)
        .sum(axis=1)
    )
    return cdm_proj_df.drop(columns=year_cols)