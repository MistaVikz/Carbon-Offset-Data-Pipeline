
def process_credits_data(credits_df, registry_code):
    # Extract registry code and numeric ID from project_id
    credits_df[['registry_code', 'numeric_id']] = credits_df['project_id'] \
    .astype(str) \
    .str.extract(r'([A-Za-z]+)[\s\-]*(\d+)', expand=True)
    credits_df['numeric_id'] = credits_df['numeric_id'].astype(float).astype('Int64')

    # Filter for issued credits and registry code
    credits_df = credits_df[credits_df['transaction_type'] == 'issuance']
    credits_df = credits_df[credits_df['registry_code'] == registry_code]
    
    # Extract issuance year from transaction_date
    credits_df['Issuance Year'] = credits_df['transaction_date'].dt.year
    
    # Calculate average annual issued credits for each project
    issued_by_year = credits_df.groupby(['numeric_id', 'Issuance Year'])['quantity'].sum().reset_index()
    avg_issued_by_proj = issued_by_year.groupby('numeric_id')['quantity'].mean().reset_index()
    avg_issued_by_proj.rename(columns={'quantity': 'Average Annual Issued'}, inplace=True)

    return avg_issued_by_proj