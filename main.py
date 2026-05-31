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
cecarbono_code ='CCB'

def main():

    # EVERYTHING but the project data cleaning should be put into processing functions with reigstry code params

    # Load the issued credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()

    print('-------------------------------------------------------------------------------------')
    print("Processing Verra data...")
    print('-------------------------------------------------------------------------------------')
    
    # Get the total issued credits for each project in verra
    verra_issued_df = process_credits_data(credits_df, verra_code)

    # Load the verra project data from the CSV file
    try:
        verra_proj_df = pd.read_csv(f'project data\\verra_projects.csv')
    except FileNotFoundError:
        print(f"Error: 'verra_projects.csv' not found in the data folder.")
    
    # Prepare the project data
    verra_proj_df.dropna(subset=['Estimated Annual Emission Reductions'], inplace=True)
    verra_proj_df['Estimated Annual Emission Reductions'] = verra_proj_df['Estimated Annual Emission Reductions'].str.replace(",", "").astype(float)

    # Merge dataframes to include Actual ERs (only keep projects with actual ERs)
    verra_df = pd.merge(verra_proj_df, verra_issued_df, left_on='ID', right_on='numeric_id', how='inner')
    
    # Get the Estimated ERs (Estimated Annual * Number of Years)
    verra_df['Estimated Emission Reductions'] = verra_df['Estimated Annual Emission Reductions'] * verra_df['Num Years']

    # Prepare the merged data
    verra_df.rename(columns={'ID': 'Project ID'}, inplace=True)
    verra_df.drop(columns=['numeric_id','Estimated Annual Emission Reductions', 'Num Years'])
    verra_df['registry_code'] = verra_code

    # Check estimated/actual ERS
    check_estimated_and_actual(verra_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(verra_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')    
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
    
    # Merge dataframes to include Actual ERs (only keep projects with actual ERs)
    gold_df = pd.merge(gold_proj_df, gold_issued_df, left_on='GSID', right_on='numeric_id', how='inner')
    
    # Get the Estimated ERs (Estimated Annual * Number of Years)
    gold_df['Estimated Emission Reductions'] = gold_df['Estimated Annual Emission Reductions'] * verra_df['Num Years']

    # Prepare the merged data
    gold_df.rename(columns={'GSID': 'Project ID'}, inplace=True)
    gold_df.drop(columns=['numeric_id', 'Estimated Annual Emission Reductions', 'Num Years'], inplace=True)
    gold_df['registry_code'] = gold_code

    # Check estimated/actual ERS
    check_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    print(f"\nProcessed Gold Standard dataset contains {len(gold_df)} projects.")

    
if __name__ == "__main__":
    main()