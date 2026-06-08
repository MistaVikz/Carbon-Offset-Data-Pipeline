from offsets_db_data.data import catalog
from utils.validation import *

# Registry codes
verra_code = 'VCS'
gold_code = 'GLD'

# Project Files
verra_file = 'verra_projects.csv'
gold_file = 'gold_projects.csv'
cdm_file = 'IGES_CDM_DB_v13.7_20250226.xlsx'

# Required columns for datasets
unified_cols = ['Project ID', 'Project Name', 'Country', 'Project Type', 'Methodology', 'Proponent','Project Size','Estimated Emission Reductions', 'Actual Emission Reductions', 'registry_code']
CDM_only_cols = ['Project ID', 'Project Name', 'Country','Other Parties Involved',
                     'Project Participants \n(Authorized by other Parties involved)','Project Type',
                     'Supplemental Information','Project Size',  'Investment Analysis Option','Barrier Analysis',
                     'Emission Factor （EFOM）','Data vintage', 'OM Calculation Method','Emission Factor （EFBM）',
                     'Weights', 'CM Emission Factor（EFCM）','Validator','Estimated Emission Reductions', 'Actual Emission Reductions']

def main():
    # Load the credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()

    # VERRA
    print("Processing Verra data...")
    verra_proj_df = load_project_data(verra_file, 'CSV')
    verra_issued_df = process_credits_data(credits_df, verra_code)

    # Prepare the project data
    verra_proj_df.dropna(subset=['Estimated Annual Emission Reductions'], inplace=True)
    verra_proj_df['Estimated Annual Emission Reductions'] = verra_proj_df['Estimated Annual Emission Reductions'].str.replace(",", "").astype(float)
    verra_proj_df.rename(columns={'ID': 'Project ID'}, inplace=True)
    verra_proj_df.rename(columns={'Name': 'Project Name'}, inplace=True)
    verra_proj_df.rename(columns={'Country/Area': 'Country'}, inplace=True)
    verra_proj_df['Project Size'] = 'UNKNOWN'
    
    # Standardize the project data
    verra_proj_df = standardize_methodologies(verra_proj_df, verra_code)
    verra_proj_df['Project Type'] = verra_proj_df['Project Type'].apply(lambda x: standardize_technologies(x, verra_code))
    
    # Check for Verra projects with issued credits that are missing from the project dataset
    check_for_missing_projects(verra_proj_df, verra_issued_df, verra_code, 'Project ID', 'numeric_id')
    
    # Build Verra dataframe with the required columns for the unified dataset
    verra_df = build_merged_dataframe(verra_proj_df, verra_issued_df, verra_code)
    verra_df = verra_df[unified_cols].copy()

    # Check estimated/actual ERS
    check_estimated_and_actual(verra_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(verra_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')    
    print(f"\nProcessed Verra dataset contains {len(verra_df)} projects.")

    # GOLD STANDARD
    print("\nProcessing Gold Standard data...")  
    gold_proj_df = load_project_data(gold_file, 'CSV')
    gold_issued_df = process_credits_data(credits_df, gold_code)
    
    # Prepare the project data
    gold_proj_df.dropna(subset=['Estimated Annual Credits'], inplace=True)
    gold_proj_df.rename(columns={'Estimated Annual Credits': 'Estimated Annual Emission Reductions'}, inplace=True)
    gold_proj_df['Estimated Annual Emission Reductions'] = gold_proj_df['Estimated Annual Emission Reductions'].astype(float)
    gold_proj_df.rename(columns={'GSID': 'Project ID'}, inplace=True)
    gold_proj_df.rename(columns={'Size': 'Project Size'}, inplace=True)
    gold_proj_df.rename(columns={'Project Developer Name':'Proponent'}, inplace=True)

    # Standardize the project data
    gold_proj_df = standardize_methodologies(gold_proj_df, gold_code)
    gold_proj_df['Project Type'] = gold_proj_df['Project Type'].apply(lambda x: standardize_technologies(x, gold_code))
    gold_proj_df = standardize_project_size(gold_proj_df)

    # Check for Gold Standard projects with issued credits that are missing from the project dataset
    check_for_missing_projects(gold_proj_df, gold_issued_df, gold_code, 'Project ID', 'numeric_id')

    # Build Gold Dataframe with the required columns for the unified dataset
    gold_df = build_merged_dataframe(gold_proj_df, gold_issued_df, gold_code)
    gold_df = gold_df[unified_cols].copy()

    # Check estimated/actual ERS
    check_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(gold_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    print(f"\nProcessed Gold Standard dataset contains {len(gold_df)} projects.")

    # CDM
    print("\nProcessing CDM data...")
    cdm_proj_df = load_project_data(cdm_file, 'Excel', 'AllProjects', skip = 1)
    
    # Process the project data
    cdm_proj_estimated_df = get_CDM_total_estimated_ERs(cdm_proj_df)
    cdm_proj_estimated_df.rename(columns={'Type of Project ': 'Project Type'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Total Issued CERs': 'Actual Emission Reductions'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'IGES-ID': 'Project ID'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Name of CDM Project Activity': 'Project Name'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Host Party': 'Country'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Project Participants \n(Authorized by Host Party)': 'Proponent'}, inplace=True)
    cdm_proj_estimated_df.fillna({'Actual Emission Reductions': 0}, inplace=True)
    cdm_proj_estimated_df.dropna(subset=['Project ID'], inplace=True)
    cdm_proj_estimated_df.rename(columns={'Scale': 'Project Size'}, inplace=True)
    cdm_proj_estimated_df['registry_code'] = 'CDM'
    
    # Standardize the project data
    cdm_proj_estimated_df = standardize_methodologies(cdm_proj_estimated_df, 'CDM')
    cdm_proj_estimated_df['Project Type'] = cdm_proj_estimated_df['Project Type'].str.replace(',', ';').str.strip()
    cdm_proj_estimated_df['Project Type'] = cdm_proj_estimated_df['Project Type'].apply(lambda x: standardize_technologies(x, 'CDM'))
    
    # Filter to only the required columns for the unified dataset
    cdm_proj_unified_df = cdm_proj_estimated_df[unified_cols].copy()

    # Check estimated/actual ERS for CDM
    compare_estimated_and_actual(cdm_proj_unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    check_estimated_and_actual(cdm_proj_unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    print(f"\nProcessed CDM dataset contains {len(cdm_proj_unified_df)} projects.")
    
    # Create the unified dataset
    verra_df['Project ID'] = verra_df['registry_code'].astype(str) + '_' + verra_df['Project ID'].astype(str)
    gold_df['Project ID'] = gold_df['registry_code'].astype(str) + '_' + gold_df['Project ID'].astype(str)
    unified_df = pd.concat([verra_df, gold_df, cdm_proj_unified_df], ignore_index=True, sort=False)
    unified_df.drop(columns=['registry_code'], inplace=True)
    unified_df = standardize_countries(unified_df)
    unified_df = standardize_proponents(unified_df)
    
    # Validate Project Type/Country Names in the unified dataset.
    check_unified_project_types(unified_df)
    check_unified_country_names(unified_df)

    print(f"\nProcessed Unified dataset contains {len(unified_df)} projects.")

    # BUILD CDM ONLY DATASET
    # Filter to only the required columns for the CDM-only dataset and clean up the data
    # Remember to standardize countries/proponents
    cdm_proj_cdm_only_df = cdm_proj_estimated_df[CDM_only_cols].copy()
    cdm_proj_cdm_only_df.rename(columns={'Project Participants \n(Authorized by other Parties involved)': 'Additional Participant Authorized'}, inplace=True)
    cdm_proj_cdm_only_df.rename(columns={'Emission Factor （EFOM）': 'Emission Factor (EFOM)'}, inplace=True)
    cdm_proj_cdm_only_df.rename(columns={'Emission Factor （EFBM）': 'Emission Factor (EFBM)'}, inplace=True)
    cdm_proj_cdm_only_df.rename(columns={'CM Emission Factor（EFCM）': 'CM Emission Factor (EFCM)'}, inplace=True)

    # print(f"\nProcessed CDM-only dataset contains {len(cdm_proj_cdm_only_df)} projects.")
    

    
if __name__ == "__main__":
    main()