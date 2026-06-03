from offsets_db_data.data import catalog
from utils.validation import *
from utils.processing import *

# Registry codes
verra_code = 'VCS'
gold_code = 'GLD'

# Project Files
verra_file = 'verra_projects.csv'
gold_file = 'gold_projects.csv'
cdm_file = 'IGES_CDM_DB_v13.7_20250226.xlsx'

# Required CDM columns for datasets
CDM_cols_unified = ['Project ID', 'Project Name', 'Host Party', 'Type of Project', 'Num of meth', 
                    'Methodology1', 'Methodology2', 'Methodology3', 'Methodology4', 'Estimated Emission Reductions', 'Actual Emission Reductions']
CDM_cols_cdm_only = ['Project ID', 'Project Name', 'Host Party','Other Parties Involved',
                     'Project Participants \n(Authorized by other Parties involved)','Type of Project',
                     'Supplemental Information','Scale', 'Num of meth', 'Methodology1', 'Methodology2', 
                     'Methodology3', 'Methodology4', 'Investment Analysis Option','Barrier Analysis',
                     'Emission Factor （EFOM）','Data vintage', 'OM Calculation Method','Emission Factor （EFBM）',
                     'Weights', 'CM Emission Factor（EFCM）','Validator','Estimated Emission Reductions', 'Actual Emission Reductions']

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

    # Check for Verra projects with issued credits that are missing from the project dataset
    check_for_missing_projects(verra_proj_df, verra_issued_df, verra_code, 'Project ID', 'numeric_id')
    
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

    # Check for Gold Standard projects with issued credits that are missing from the project dataset
    check_for_missing_projects(gold_proj_df, gold_issued_df, gold_code, 'Project ID', 'numeric_id')

    # Build Gold Dataframe
    gold_df = build_merged_dataframe(gold_proj_df, gold_issued_df, gold_code)

    # Check estimated/actual ERS
    check_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    print(f"\nProcessed Gold Standard dataset contains {len(gold_df)} projects.")

    # CDM
    print("\nProcessing CDM data...")

    # Get project and issued data for CDM
    cdm_proj_df = load_project_data(cdm_file, 'Excel', 'AllProjects', skip = 1)
    
    # Process the project data
    cdm_proj_estimated_df = get_CDM_total_estimated_ERs(cdm_proj_df)
    cdm_proj_estimated_df.rename(columns={'Type of Project ': 'Type of Project'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Total Issued CERs': 'Actual Emission Reductions'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'IGES-ID': 'Project ID'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Name of CDM Project Activity': 'Project Name'}, inplace=True)
    cdm_proj_estimated_df.fillna({'Actual Emission Reductions': 0}, inplace=True)
    cdm_proj_estimated_df.dropna(subset=['Project ID'], inplace=True)

    # Filter to only the required columns for the unified CDM datasets
    cdm_proj_unified_df = cdm_proj_estimated_df[CDM_cols_unified].copy()

    # Filter to only the required columns for the CDM-only dataset and clean up the data
    cdm_proj_cdm_only_df = cdm_proj_estimated_df[CDM_cols_cdm_only].copy()
    cdm_proj_cdm_only_df.rename(columns={'Project Participants \n(Authorized by other Parties involved)': 'Additional Participant Authorized'}, inplace=True)
    cdm_proj_cdm_only_df.rename(columns={'Emission Factor （EFOM）': 'Emission Factor (EFOM)'}, inplace=True)
    cdm_proj_cdm_only_df.rename(columns={'Emission Factor （EFBM）': 'Emission Factor (EFBM)'}, inplace=True)
    cdm_proj_cdm_only_df.rename(columns={'CM Emission Factor（EFCM）': 'CM Emission Factor (EFCM)'}, inplace=True)

    # Check estimated/actual ERS for CDM
    compare_estimated_and_actual(cdm_proj_unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    check_estimated_and_actual(cdm_proj_unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')

    print(f"\nProcessed CDM dataset contains {len(cdm_proj_unified_df)} projects.")
    print(f"\nProcessed CDM-only dataset contains {len(cdm_proj_cdm_only_df)} projects.")
    
    # Final output should have CDM only and VERRA/GOLD/CDM combined dataset.

if __name__ == "__main__":
    main()