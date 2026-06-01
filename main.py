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

# Project Files
verra_file = 'verra_projects.csv'
gold_file = 'gold_projects.csv'
cdm_file = 'IGES_CDM_DB_v13.7_20250226.xlsx'

def main():
    # Load the credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()

    # VERRA
    print("Processing Verra data...")
    
    # Get the Verra project data and processed issue data
    verra_proj_df = load_project_data(verra_file, 'CSV')
    verra_issued_df = process_credits_data(credits_df, verra_code)
    
    # Prepare the project data
    verra_proj_df.dropna(subset=['Estimated Annual Emission Reductions'], inplace=True)
    verra_proj_df['Estimated Annual Emission Reductions'] = verra_proj_df['Estimated Annual Emission Reductions'].str.replace(",", "").astype(float)
    verra_proj_df.rename(columns={'ID': 'Project ID'}, inplace=True)

    # Build Verra dataframe
    verra_df = build_merged_dataframe(verra_proj_df, verra_issued_df, verra_code)

    # Check estimated/actual ERS
    check_estimated_and_actual(verra_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(verra_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')    
    print(f"\nProcessed Verra dataset contains {len(verra_df)} projects.")

    # GOLD STANDARD
    print("\nProcessing Gold Standard data...")
   
    # Get the total issued credits for each project in gold standard
    gold_proj_df = load_project_data(gold_file, 'CSV')
    gold_issued_df = process_credits_data(credits_df, gold_code)
    
    # Prepare the project data
    gold_proj_df.dropna(subset=['Estimated Annual Credits'], inplace=True)
    gold_proj_df.rename(columns={'Estimated Annual Credits': 'Estimated Annual Emission Reductions'}, inplace=True)
    gold_proj_df['Estimated Annual Emission Reductions'] = gold_proj_df['Estimated Annual Emission Reductions'].astype(float)
    gold_proj_df.rename(columns={'GSID': 'Project ID'}, inplace=True)

    # Build Gold Dataframe
    gold_df = build_merged_dataframe(gold_proj_df, gold_issued_df, gold_code)

    # Check estimated/actual ERS
    check_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    print(f"\nProcessed Gold Standard dataset contains {len(gold_df)} projects.")

    
if __name__ == "__main__":
    main()