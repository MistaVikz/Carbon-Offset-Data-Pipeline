from offsets_db_data.data import catalog
from utils.validation import *
from utils.io import *
from utils.processing import *

# Registry codes
verra_code = 'VCS'
gold_code = 'GLD'

# Project Files
cdm_file = 'project data\\cdm_projects.xlsx'

# Required columns for datasets
unified_cols = ['Project ID', 'Project Name', 'Country', 'Methodology 1', 'Methodology 2', 'Methodology 3',
                    'Methodology 4', 'Project Size', 'Estimated Emission Reductions', 
                    'Actual Emission Reductions', 'registry_code']
CDM_only_cols = ['Project ID', 'Project Name', 'Country', 'Other Countries Involved', 'Methodology 1', 
                    'Methodology 2', 'Methodology 3', 'Methodology 4', 'Project Size', 
                    'Investment Analysis Option','Barrier Analysis', 'Emission Factor Data Vintage', 
                    'Emission Factor Weights', 'Validator', 'Estimated Emission Reductions', 
                    'Actual Emission Reductions']
meth_cols = ['Methodology 1', 'Methodology 2', 'Methodology 3', 'Methodology 4']

def main():
    # Get command line arguments
    args = parse_args()
    download_verra = args.verra
    download_gold = args.gold
    download_cdm = args.cdm
    master_input_file = args.create_master_gold

    # Load the credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()
    
    # VERRA DATASET
    print('VERRA')
    verra_proj_df = update_and_load_verra_data(download_verra, 'utf-8')
    verra_issued_df = process_credits_data(credits_df, verra_code)

    # Prepare the project data
    verra_proj_df.dropna(subset=['Estimated Annual Emission Reductions', 'Methodology'], inplace=True)
    verra_proj_df['Estimated Annual Emission Reductions'] = verra_proj_df['Estimated Annual Emission Reductions'].str.replace(",", "").astype(float)
    verra_proj_df.rename(columns={'ID': 'Project ID'}, inplace=True)
    verra_proj_df.rename(columns={'Name': 'Project Name'}, inplace=True)
    verra_proj_df.rename(columns={'Country/Area': 'Country'}, inplace=True)
    verra_proj_df['Project Size'] = 'UNKNOWN'
    verra_proj_df = process_methodologies(verra_proj_df, verra_code)
    
    # Validate and build the merged dataframe
    check_for_missing_projects(verra_proj_df, verra_issued_df, verra_code, 'Project ID', 'numeric_id')
    verra_df = build_merged_dataframe(verra_proj_df, verra_issued_df, verra_code)
    verra_df = verra_df[unified_cols].copy()
    print(f"\nVerra dataset contains {len(verra_df)} projects.\n")

    # GOLD STANDARD DATASET
    print("GOLD STANDARD")

    # Create master gold standard csv, if specified in command arguments
    if master_input_file:
        print(f'Creating new Gold Standard dataset from {master_input_file}.')
        create_master_gold_csv(master_input_file)

    gold_proj_df = update_and_load_gold_data(download_gold)
    gold_issued_df = process_credits_data(credits_df, gold_code)

    # Prepare the project data
    gold_proj_df.rename(columns={'estimated_annual_credits': 'Estimated Annual Emission Reductions'}, inplace=True)
    gold_proj_df.dropna(subset=['Estimated Annual Emission Reductions'], inplace=True)
    gold_proj_df['Estimated Annual Emission Reductions'] = gold_proj_df['Estimated Annual Emission Reductions'].astype(float)
    gold_proj_df.rename(columns={'gsid': 'Project ID'}, inplace=True)
    gold_proj_df['Project ID'] = gold_proj_df['Project ID'].astype(int)
    gold_proj_df.rename(columns={'size': 'Project Size'}, inplace=True)
    gold_proj_df.rename(columns={'developer':'Proponent'}, inplace=True)
    gold_proj_df.rename(columns={'country':'Country'}, inplace=True)
    gold_proj_df.dropna(subset=['Country'], inplace=True)
    gold_proj_df.rename(columns={'project_type':'Project Type'}, inplace=True)
    gold_proj_df.rename(columns={'methodology':'Methodology'}, inplace=True)
    gold_proj_df.dropna(subset=['Methodology'], inplace=True)
    gold_proj_df.rename(columns={'name':'Project Name'}, inplace=True)
    gold_proj_df['registry_code'] = gold_code
    gold_proj_df = process_methodologies(gold_proj_df, gold_code)
    gold_proj_df = standardize_project_size(gold_proj_df)
    
    # Validate and build the gold standard dataframe
    check_for_missing_projects(gold_proj_df, gold_issued_df, gold_code, 'Project ID', 'numeric_id')
    gold_df = build_merged_dataframe(gold_proj_df, gold_issued_df, gold_code)
    gold_df = gold_df[unified_cols].copy()
    print(f"\nGold Standard dataset contains {len(gold_df)} projects.\n")

    # CDM-ONLY DATASET
    cdm_proj_df = update_and_load_cdm_data(download_cdm, 'AllProjects', skip = 1)
    
    # Prepare the CDM data
    cdm_proj_estimated_df = get_CDM_total_estimated_ERs(cdm_proj_df)
    cdm_proj_estimated_df.rename(columns={'Type of Project ': 'Project Type'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Total Issued CERs': 'Actual Emission Reductions'}, inplace=True)
    cdm_proj_estimated_df.dropna(subset=['Methodology1'], inplace=True)
    cdm_proj_estimated_df.fillna({'Actual Emission Reductions': 0}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'IGES-ID': 'Project ID'}, inplace=True)
    cdm_proj_estimated_df.dropna(subset=['Project ID'], inplace=True)
    cdm_proj_estimated_df.rename(columns={'Name of CDM Project Activity': 'Project Name'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Host Party': 'Country'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Data vintage': 'Emission Factor Data Vintage'}, inplace=True)
    cdm_proj_estimated_df.fillna({'Emission Factor Data Vintage' : 'N.A.'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Scale': 'Project Size'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Other Parties Involved': 'Other Countries Involved'}, inplace=True)
    cdm_proj_estimated_df.rename(columns={'Weights': 'Emission Factor Weights'}, inplace=True)
    cdm_proj_estimated_df.fillna({'Emission Factor Weights' : 'N.A.'}, inplace=True)
    cdm_proj_estimated_df['registry_code'] = 'CDM' 
    cdm_proj_estimated_df = process_methodologies(cdm_proj_estimated_df, 'CDM')
    
    # Filter to only the required columns for the CDM-only dataset
    cdm_proj_cdm_only_df = cdm_proj_estimated_df[CDM_only_cols].copy()

    # Standardize columns specifically for CDM-Only
    cdm_proj_cdm_only_df = standardize_countries(cdm_proj_cdm_only_df, 'Country')
    cdm_proj_cdm_only_df = standardize_countries(cdm_proj_cdm_only_df, 'Other Countries Involved')
    cdm_proj_cdm_only_df = standardize_analysis(cdm_proj_cdm_only_df, 'Investment Analysis Option')
    cdm_proj_cdm_only_df = standardize_analysis(cdm_proj_cdm_only_df, 'Barrier Analysis')
    for col_name in meth_cols:
        cdm_proj_cdm_only_df = standardize_methodology(cdm_proj_cdm_only_df, col_name)

    # Validate the CDM Only Dataset
    print("CDM - ONLY")
    check_canonical_names(cdm_proj_cdm_only_df, 'Country')
    check_canonical_names(cdm_proj_cdm_only_df, 'Other Countries Involved')
    for col_name in meth_cols:
        check_canonical_names(cdm_proj_cdm_only_df, col_name, 'Methodology')

    compare_estimated_and_actual(cdm_proj_cdm_only_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    check_estimated_and_actual(cdm_proj_cdm_only_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    print(f"\nCDM-only dataset contains {len(cdm_proj_cdm_only_df)} projects.\n")
    
    # UNIFED DATASET
    # Filter CDM to only the required columns for the unified dataset
    cdm_proj_unified_df = cdm_proj_estimated_df[unified_cols].copy()

    # Create the unified dataset
    verra_df['Project ID'] = verra_df['registry_code'].astype(str) + '_' + verra_df['Project ID'].astype(str)
    gold_df['Project ID'] = gold_df['registry_code'].astype(str) + '_' + gold_df['Project ID'].astype(str)
    unified_df = pd.concat([verra_df, gold_df, cdm_proj_unified_df], ignore_index=True, sort=False)
    unified_df.drop(columns=['registry_code'], inplace=True)

    # Standardize Column Values
    unified_df = standardize_countries(unified_df, 'Country')
    for col_name in meth_cols:
        unified_df = standardize_methodology(unified_df, col_name)
    
    # Validate the unified dataset.
    print("UNIFIED")
    check_canonical_names(unified_df, 'Country')
    for col_name in meth_cols:
        check_canonical_names(unified_df, col_name, 'Methodology')
    
    check_estimated_and_actual(unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    compare_estimated_and_actual(unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
    print(f"\nUnified dataset contains {len(unified_df)} projects.")

    # Output the datasets
    cdm_proj_cdm_only_df.to_csv('output\\cdm_dataset.csv')
    unified_df.to_csv('output\\unified_dataset.csv')
    print('\nDatasets saved to output directory.')
if __name__ == "__main__":
    main()