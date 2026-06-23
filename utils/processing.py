import pandas as pd

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
    """
    Sum CDM annual columns to produce a total estimated emission reductions column.

    Parameters
    ----------
    cdm_proj_df : pandas.DataFrame
        CDM project table containing year columns named as integers (e.g., 2005, 2006).
        Year columns expected to fall within the 2000–2047 range.

    Returns
    -------
    pandas.DataFrame
        A copy of `cdm_proj_df` with:
        - a new column `'Estimated Emission Reductions'` equal to the row-wise sum across detected year columns (NaNs treated as zero),
        - and the original year columns removed.

    Raises
    ------
    ValueError
        If no integer year columns within 2000–2047 are found.
    """
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

def process_methodologies(proj_df, registry_code = 'CDM'):
    """
    Apply separate rules for Verra, Gold Standard and CDM to standardize the formatting for all
    registries. Split rows with multiple methodologies into separate columns Methodology 1, 
    Methodology 2, Methodology 3, and Methodology 4 (Verra/Gold).
    All projects must have a Methodology 1, but Methodologies 2-4 can be None.

    Parameters
    ----------
    proj_df : pandas.DataFrame
        Dataframe with Methodology columns.
    registry_code : str
        Registry identifier. Default = CDM.

    Returns
    -------
    pandas.DataFrame
        A copy of `proj_df` with:
        - Formatted Methodology 1, Methodology 2, Methodology 3, and Methodology 4
        columns.
    """
    proj_df = proj_df.copy()

    if registry_code == 'VCS':
        # Format Original Column
        proj_df['Methodology'] = proj_df['Methodology'].str.replace('.', '').str.strip()
        proj_df['Methodology'] = proj_df['Methodology'] + ';'
    
        # Split methodologies by ';' and assign to separate columns
        split_methods = proj_df['Methodology'].str.split(';')
        split_methods = split_methods.apply(lambda x: [m.strip() for m in x if m.strip()])   
        for i in range(1, 5):
            proj_df[f'Methodology {i}'] = split_methods.apply(lambda x: x[i-1] if len(x) > i-1 else 'None')
    
    elif registry_code == 'GLD':
        # For methodologies starting with 'A', keep only the code (e.g., 'ACM0018', 'AM0022', etc.)
        mask = proj_df['Methodology'].str.startswith('A')
        proj_df.loc[mask, 'Methodology'] = proj_df.loc[mask, 'Methodology'].str.split(n=1).str[0]

        # Format the Original Column
        proj_df['Methodology'] = proj_df['Methodology'].replace({'nan': 'None'})
        proj_df['Methodology'] = proj_df['Methodology'].replace({'Not provided': 'Not Provided'})
        proj_df['Methodology'] = proj_df['Methodology'] + ';'
    
        # Split methodologies by ';' and assign to separate columns
        split_methods = proj_df['Methodology'].str.split(';')
        split_methods = split_methods.apply(lambda x: [m.strip() for m in x if m.strip()])   
        for i in range(1, 5):
            proj_df[f'Methodology {i}'] = split_methods.apply(lambda x: x[i-1] if len(x) > i-1 else 'None')

        # Drop projects with no methodology.

    elif registry_code == 'CDM':
        proj_df = proj_df.rename(columns={
        'Methodology1': 'Methodology 1',
        'Methodology2': 'Methodology 2',
        'Methodology3': 'Methodology 3',
        'Methodology4': 'Methodology 4'
        })

    # Assign n/a values in Methodology 2-4 as "None". 
    proj_df['Methodology 2'] = proj_df['Methodology 2'].fillna('None')
    proj_df['Methodology 3'] = proj_df['Methodology 3'].fillna('None')
    proj_df['Methodology 4'] = proj_df['Methodology 4'].fillna('None')

    return proj_df