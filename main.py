import pandas as pd

from offsets_db_data.data import catalog
from utils.validation import *
from utils.processing import *

# Define mapping of registry codes to project data files
registry_map = {'VCS': 'verra_projects.csv'}

def main():
    
    # Load the issued credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()
    
    proccessed_issued_df = process_credits_data(credits_df, registry_map['VCS'])

    print(proccessed_issued_df.head())
    print(proccessed_issued_df.info())
    
    for registry_code, proj_file in registry_map.items():
        try:
            proj_df = pd.read_csv(f'project data\\{proj_file}')
        except FileNotFoundError:
            print(f"Error: '{proj_file}' not found in the raw data folder.")
            continue

    # Prepare the official project data
    #proj_df.dropna(subset=['Estimated Annual Emission Reductions'], inplace=True)
    #proj_df['Estimated Annual Emission Reductions'] = proj_df['Estimated Annual Emission Reductions'].str.replace(",", "").astype(float)
    #print(proj_df.head())
    #print(proj_df.info())



if __name__ == "__main__":
    main()