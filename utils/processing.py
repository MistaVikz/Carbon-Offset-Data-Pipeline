
def process_credits_data(credits_df, registry_code):
    # Extract registry code and numeric ID from project_id
    credits_df[['registry_code', 'numeric_id']] = credits_df['project_id'] \
        .astype(str) \
        .str.extract(r'([A-Za-z]+)[\s\-]*(\d+)', expand=True)
    credits_df['numeric_id'] = credits_df['numeric_id'].astype(float).astype('Int64')

    # Need to Account for cancellation
    print(credits_df['transaction_type'].value_counts())

    # Filter for issued credits and registry code
    credits_df = credits_df[credits_df['transaction_type'] == 'issuance']
    credits_df = credits_df[credits_df['registry_code'] == registry_code]

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