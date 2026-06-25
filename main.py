from offsets_db_data.data import catalog
from utils.validation import *
from utils.io import *
from utils.processing import *
import warnings

# Registry codes
verra_code = 'VCS'
gold_code = 'GLD'
cdm_code = 'CDM'

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
    update_verra = args.verra_update
    update_gold = args.gold_update
    update_cdm = args.cdm_update
    include_verra = args.verra_include
    include_gold = args.gold_include
    include_cdm = args.cdm_include
    include_cdm_only = args.cdm_only
    master_input_file = args.create_master_gold


    # DELETE After Debugging
    update_verra = False
    update_gold = False
    update_cdm = False
    include_verra = True
    include_gold = True
    include_cdm = True
    include_cdm_only = False


    # Load the credits data from the catalog
    credits = catalog['credits']
    credits_df = credits.read()
    
    # Verra
    print('VERRA')
    print('--------------------------------------------------------------------------------------------------')    
    if include_verra:
        verra_proj_df = update_and_load_verra_data(update_verra, 'utf-8')
        verra_issued_df = process_credits_data(credits_df, verra_code)

        # Prepare the project data
        num_verra_original = len(verra_proj_df)
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
        print(f"\nVerra Dataset contains {len(verra_df)} / {num_verra_original} projects.\n")
    else:
        print("Verra excluded from the Unified Dataset.\n")

    # Gold Standard
    print("GOLD STANDARD")
    print('--------------------------------------------------------------------------------------------------')
    if include_gold:
        # Create master gold standard csv, if specified in command arguments
        if master_input_file:
            print(f'Creating new Gold Standard dataset from {master_input_file}.')
            create_master_gold_csv(master_input_file)

        gold_proj_df = update_and_load_gold_data(update_gold)
        gold_issued_df = process_credits_data(credits_df, gold_code)

        # Prepare the project data
        num_gold_original = len(gold_proj_df)
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
        print(f"\nGold Standard Dataset contains {len(gold_df)} / {num_gold_original} projects.\n")
    else:
        print("Gold Standard excluded from the Unified Dataset.\n")

    print('CDM')
    print('--------------------------------------------------------------------------------------------------')    
    if include_cdm:
        # # Prepare the CDM data
        cdm_proj_df = update_and_load_cdm_data(update_cdm, 'AllProjects', skip = 1)
        num_cdm_original = len(cdm_proj_df)
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
        cdm_proj_estimated_df = process_methodologies(cdm_proj_estimated_df, cdm_code)
    
        # Create CDM-only Dataset
        if include_cdm_only: 
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
            print('--------------------------------------------------------------------------------------------------')
            check_canonical_names(cdm_proj_cdm_only_df, 'Country')
            check_canonical_names(cdm_proj_cdm_only_df, 'Other Countries Involved')
            for col_name in meth_cols:
                check_canonical_names(cdm_proj_cdm_only_df, col_name, 'Methodology')

            compare_estimated_and_actual(cdm_proj_cdm_only_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
            check_estimated_and_actual(cdm_proj_cdm_only_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
            print(f"\nCDM-Only Dataset contains {len(cdm_proj_cdm_only_df)} / {num_cdm_original} projects.")
    else:
        print("CDM excluded from the Unified Dataset.\n")

    # UNIFED DATASET
    if include_verra or include_gold or include_cdm:
        # Create the unified dataset 
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            unified_df = pd.DataFrame(columns=unified_cols)
            if include_verra:
                verra_df['Project ID'] = verra_df['registry_code'].astype(str) + '_' + verra_df['Project ID'].astype(str)
                unified_df = pd.concat([verra_df, unified_df], ignore_index=True, sort=False)
            if include_gold:
                gold_df['Project ID'] = gold_df['registry_code'].astype(str) + '_' + gold_df['Project ID'].astype(str)
                unified_df = pd.concat([gold_df, unified_df], ignore_index=True, sort=False)
            if include_cdm:
                cdm_proj_unified_df = cdm_proj_estimated_df[unified_cols].copy()
                unified_df = pd.concat([cdm_proj_unified_df, unified_df], ignore_index=True, sort=False)
        unified_df.drop(columns=['registry_code'], inplace=True)

        # Standardize Column Values
        unified_df = standardize_countries(unified_df, 'Country')
        for col_name in meth_cols:
            unified_df = standardize_methodology(unified_df, col_name)
    
        # Validate the unified dataset.
        print("UNIFIED")
        print('--------------------------------------------------------------------------------------------------')
        check_canonical_names(unified_df, 'Country')
        for col_name in meth_cols:
            check_canonical_names(unified_df, col_name, 'Methodology')
    
        check_estimated_and_actual(unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
        compare_estimated_and_actual(unified_df, 'Estimated Emission Reductions', 'Actual Emission Reductions')
        print(f"\nUnified Dataset contains {len(unified_df)} projects.")
    else:
        print('Unified Dataset not create as all registries have been excluded.')

    # Save time-stamped output
    if(include_cdm_only):
        output_folder = create_output_folder(include_cdm_only)
        save_dataset(output_folder, cdm_proj_cdm_only_df, is_cdm_only = True)
        save_dataset(output_folder, unified_df, is_cdm_only = False, has_verra=include_verra, 
                     has_gold=include_gold, has_cdm=include_cdm)
    else:
        output_folder = create_output_folder()
        save_dataset(output_folder, unified_df, is_cdm_only = False, has_verra=include_verra, 
                     has_gold=include_gold, has_cdm=include_cdm)

if __name__ == "__main__":
    main()