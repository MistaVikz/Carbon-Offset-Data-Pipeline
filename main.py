import pandas as pd
from offsets_db_data.data import catalog
from utils.validation import *
from utils.processing import *

# Registry codes
verra_code = 'VCS'
gold_code = 'GLD'
car_code = 'CAR'
acr_code = 'ACR'
vcr_code = 'VCR'

def main():
    
    # Load the issued credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()

    # Get the annual average issued credits for each project in verra
    proccessed_issued_df = process_credits_data(credits_df, verra_code)

    # Load the verra project data from the CSV file
    try:
        proj_df = pd.read_csv(f'project data\\verra_projects.csv')
    except FileNotFoundError:
        print(f"Error: 'verra_projects.csv' not found in the data folder.")
    
    # Prepare the project data
    proj_df.dropna(subset=['Estimated Annual Emission Reductions'], inplace=True)
    proj_df['Estimated Annual Emission Reductions'] = proj_df['Estimated Annual Emission Reductions'].str.replace(",", "").astype(float)
    
    # Merge dataframes to compare annual estimated ERs with average annual issued credits
    verra_df = pd.merge(proj_df, proccessed_issued_df, left_on='ID', right_on='numeric_id', how='left')
    verra_df['Average Annual Issued'] = verra_df['Average Annual Issued'].fillna(0)
    verra_df.drop(columns=['numeric_id', 'AFOLU Activities', 'Project Registration Date', 'Crediting Period Start Date', 'Crediting Period End Date', 'Region'], inplace=True)
    verra_df.rename(columns={'ID': 'Project ID'}, inplace=True)
    verra_df['registry_code'] = verra_code

    # Check for projects where average annual issued credits exceed estimated ERs
    compare_estimated_and_issued(verra_df, 'Project ID', 'Estimated Annual Emission Reductions', 'Average Annual Issued')
    check_estimated_with_no_issued(verra_df, 'Project ID', 'Estimated Annual Emission Reductions', 'Average Annual Issued')

    print(verra_df.head())
    print(verra_df.info())


if __name__ == "__main__":
    main()