import pandas as pd
from offsets_db_data.data import catalog
from utils.validation import *
from utils.processing import *

# Registry codes
verra_code = 'VCS'
gold_code = 'GLD'
car_code = 'CAR'
acr_code = 'ACR'
art_code = 'ART'

def main(): 
    # Load the issued credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()

    print('-------------------------------------------------------------------------------------')
    print("Processing Verra data...")
    print('-------------------------------------------------------------------------------------')
    # Get the annual average issued credits for each project in verra
    verra_issued_df = process_credits_data(credits_df, verra_code)

    # Load the verra project data from the CSV file
    try:
        verra_proj_df = pd.read_csv(f'project data\\verra_projects.csv')
    except FileNotFoundError:
        print(f"Error: 'verra_projects.csv' not found in the data folder.")
    
    # Prepare the project data
    verra_proj_df.dropna(subset=['Estimated Annual Emission Reductions'], inplace=True)
    verra_proj_df['Estimated Annual Emission Reductions'] = verra_proj_df['Estimated Annual Emission Reductions'].str.replace(",", "").astype(float)
    
    # Merge dataframes to compare annual estimated ERs with average annual issued credits
    verra_df = pd.merge(verra_proj_df, verra_issued_df, left_on='ID', right_on='numeric_id', how='left')
    verra_df['Average Annual Issued'] = verra_df['Average Annual Issued'].fillna(0)
    
    # Prepare the merged data
    verra_df.rename(columns={'ID': 'Project ID'}, inplace=True)
    verra_df.drop(columns='numeric_id')
    verra_df['registry_code'] = verra_code

    # Check estimated/actual ERS
    check_estimated_with_no_issued(verra_df, 'Estimated Annual Emission Reductions', 'Average Annual Issued')
    compare_estimated_and_issued(verra_df, 'Estimated Annual Emission Reductions', 'Average Annual Issued')
    
    print(f"\nProcessed Verra dataset contains {len(verra_df)} projects.")
    
    print('\n-------------------------------------------------------------------------------------')
    print("Processing Gold Standard data...")
    print('-------------------------------------------------------------------------------------')

    # Get the annual average issued credits for each project in gold standard
    gold_issued_df = process_credits_data(credits_df, gold_code)

    # Load the gold standard project data from the CSV file
    try:
        gold_proj_df = pd.read_csv(f'project data\\gold_projects.csv')
    except FileNotFoundError:
        print(f"Error: 'gold_projects.csv' not found in the data folder.")
    
    # Prepare the project data
    gold_proj_df.dropna(subset=['Estimated Annual Credits'], inplace=True)
    gold_proj_df.rename(columns={'Estimated Annual Credits': 'Estimated Annual Emission Reductions'}, inplace=True)
    gold_proj_df['Estimated Annual Emission Reductions'] = gold_proj_df['Estimated Annual Emission Reductions'].astype(float)
    
    # Merge dataframes to compare annual estimated ERs with average annual issued credits
    gold_df = pd.merge(gold_proj_df, gold_issued_df, left_on='GSID', right_on='numeric_id', how='left')
    gold_df['Average Annual Issued'] = verra_df['Average Annual Issued'].fillna(0)

    # Prepare the merged data
    gold_df.rename(columns={'GSID': 'Project ID'}, inplace=True)
    gold_df.drop(columns='numeric_id', inplace=True)
    gold_df['registry_code'] = gold_code

    # Check estimated/actual ERS
    check_estimated_with_no_issued(gold_df, 'Estimated Annual Emission Reductions', 'Average Annual Issued')
    compare_estimated_and_issued(gold_df, 'Estimated Annual Emission Reductions', 'Average Annual Issued')
    
    print(f"\nProcessed Gold Standard dataset contains {len(gold_df)} projects.")

if __name__ == "__main__":
    main()