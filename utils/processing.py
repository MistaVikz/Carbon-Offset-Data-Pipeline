import pandas as pd

def process_credits_data(credits_df, registry_code):
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
    # Merge dataframes to include Actual ERs (only keep projects with actual ERs)
    merged_df = pd.merge(proj_df, issued_df, left_on='Project ID', right_on='numeric_id', how='inner')
    
    # Get the Estimated ERs (Estimated Annual * Number of Years)
    merged_df['Estimated Emission Reductions'] = merged_df['Estimated Annual Emission Reductions'] * merged_df['Num Years']

    # Prepare the merged data
    merged_df.drop(columns=['numeric_id','Estimated Annual Emission Reductions', 'Num Years'])
    merged_df['registry_code'] = registry_code

    return merged_df