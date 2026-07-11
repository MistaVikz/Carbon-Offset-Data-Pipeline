from utils.standards import *
from utils.io import *

def check_for_missing_projects(proj_df, issued_df, registry_code, project_id_col='Project ID', issued_id_col='numeric_id'):
    """
    Flag issued-credit projects that are missing from the project dataset.

    Parameters
    ----------
    proj_df : pandas.DataFrame
        Dataframe of project records to compare against.
    issued_df : pandas.DataFrame
        Dataframe of issued-credit records.
    registry_code : str
        Registry code used in warning messages.
    project_id_col : str, optional
        Column name in the project dataframe for project IDs. Default is 'Project ID'.
    issued_id_col : str, optional
        Column name in the issued dataframe for project IDs. Default is 'numeric_id'.

    Returns
    -------
    None
    """
    missing_proj = issued_df[~issued_df[issued_id_col].isin(proj_df[project_id_col])]
    if len(missing_proj) > 0:
        print(f"\nWARNING: {len(missing_proj)} project(s) with issued credits in registry {registry_code} have missing/incomplete project data.")
        add_warning_entry(
            f"Projects with issued credits in registry {registry_code} missing from the project dataset:",
            missing_proj[[issued_id_col, 'Actual Emission Reductions']]
        )
        
def compare_estimated_and_actual(df, estimated_col, actual_col, ACTUAL_THRESHOLD=50., EQUAL_THRESHOLD=10.):
    """
    Identify projects where actual emission reductions exceed or equal estimates.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe containing estimated and actual emission reduction values.
    estimated_col : str
        Column name for estimated emission reductions.
    actual_col : str
        Column name for actual emission reductions.
    ACTUAL_THRESHOLD : float, optional
        Percentage threshold above which warnings are logged for actual > estimated. Default is 50.
    EQUAL_THRESHOLD : float, optional
        Percentage threshold above which warnings are logged for actual == estimated. Default is 10.

    Returns
    -------
    None
    """
    actual_greater_than_estimated = df[df[actual_col] > df[estimated_col]]
    actual_equal_to_estimated = df[df[actual_col] == df[estimated_col]]

    actual_greater_than_estimate_per = len(actual_greater_than_estimated) / len(df) * 100 if len(df) else 0
    actual_equal_to_estimate_per = len(actual_equal_to_estimated) / len(df) * 100 if len(df) else 0

    if actual_greater_than_estimate_per > ACTUAL_THRESHOLD:
        print(f"WARNING: {actual_greater_than_estimate_per:.2f}% of projects have Actual Emission Reductions exceed the Estimated Emission Reductions.")
        add_warning_entry(
            f"Projects where Actual Emission Reductions exceed Estimated Emission Reductions ({actual_greater_than_estimate_per:.2f}% of projects):",
            get_display_subset(actual_greater_than_estimated, ['Project ID', 'Project Name', estimated_col, actual_col])
        )

    if actual_equal_to_estimate_per > EQUAL_THRESHOLD:
        print(f"WARNING: {actual_equal_to_estimate_per:.2f}% of projects have Actual Emission Reductions equal the Estimated Emission Reductions.")
        add_warning_entry(
            f"Projects where Actual Emission Reductions equal Estimated Emission Reductions ({actual_equal_to_estimate_per:.2f}% of projects):",
            get_display_subset(actual_equal_to_estimated, ['Project ID', 'Project Name', estimated_col, actual_col])
        )

def check_estimated_and_actual(df, estimated_col, actual_col):
    """
    Flag projects with missing, negative, or inconsistent emission reduction values.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe containing estimated and actual emission reduction values.
    estimated_col : str
        Column name for estimated emission reductions.
    actual_col : str
        Column name for actual emission reductions.

    Returns
    -------
    None
    """
    missing_estimated = df[(df[estimated_col] == 0) & (df[actual_col] > 0)]
    negative_estimated = df[df[estimated_col] < 0]
    negative_actual = df[df[actual_col] < 0]

    if len(missing_estimated) > 0:
        print(f"WARNING: {len(missing_estimated)} project(s) has/have no Estimated Emission Reductions but have Actual Emission Reductions.")
        add_warning_entry(
            "Projects with no Estimated Emission Reductions but with Actual Emission Reductions:",
            get_display_subset(missing_estimated, ['Project ID', 'Project Name', estimated_col, actual_col])
        )

    if len(negative_estimated) > 0:
        print(f"WARNING: {len(negative_estimated)} project(s) has/have negative Estimated Emision Reductions.")
        add_warning_entry(
            "Projects with negative Estimated Emission Reductions:",
            get_display_subset(negative_estimated, ['Project ID', 'Project Name', estimated_col, actual_col])
        )

    if len(negative_actual) > 0:
        print(f"WARNING: {len(negative_actual)} project(s) has/have negative Actual Emision Reductions.")
        add_warning_entry(
            "Projects with negative Actual Emission Reductions:",
            get_display_subset(negative_actual, ['Project ID', 'Project Name', estimated_col, actual_col])
        )

def check_canonical_names(df, col, type='Country'):
    """
    Validate that country or methodology values match the canonical mappings.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe containing the column to validate.
    col : str
        Column name to validate.
    type : str, optional
        Either 'Country' or another label used for the mapping type. Default is 'Country'.

    Returns
    -------
    None
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("`df` must be a pandas DataFrame")
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found in dataframe")

    def _is_valid_name(name):
        if pd.isna(name):
            return False

        if type == 'Country':
            if col == 'Other Countries Involved':
                if name == 'No Additional Countries' or name == 'Multiple Additional Countries':
                    return True
        else:
            if name == 'Other':
                return True
            if col != 'Methodology 1' and name == 'None':
                return True

        s = str(name).strip()
        if s == '':
            return False

        if type == 'Country':
            return normalize_label(s) in COUNTRY_LOOKUP
        else:
            return normalize_label(s) in METHODOLOGY_LOOKUP

    mask_invalid = ~df[col].apply(_is_valid_name)
    out = df.loc[mask_invalid].copy()
    if not out.empty:
        out[f'Invalid {type}'] = out[col]
        print(f"WARNING: {len(out)} project(s) has/have invalid {col} values. Update {type} mapping JSON or correct the {type} names. See warning_log.txt at the end of the run.")
        add_warning_entry(f"Invalid {type} values found in column {col}:", out)
    return

def remove_duplicate_projects(df):
    """
    Remove Verra/Gold Standard projects that match CDM projects by project name and methodology/country signature.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe containing project records from all registries.

    Returns
    -------
    pandas.DataFrame
        A dataframe with duplicate Verra/Gold Standard projects removed.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("`df` must be a pandas DataFrame")

    required_cols = [
        'Project Name',
        'Country',
        'Methodology 1',
        'Methodology 2',
        'Methodology 3',
        'Methodology 4',
        'registry_code',
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns for duplicate detection: {missing_cols}")

    key_cols = ['Country', 'Methodology 1', 'Methodology 2', 'Methodology 3', 'Methodology 4']

    candidate_df = df.copy()

    for col in key_cols:
        candidate_df[col] = candidate_df[col].fillna('None')

    candidate_df['Project Name'] = candidate_df['Project Name'].fillna('UNKNOWN')
    candidate_df['Country'] = candidate_df['Country'].fillna('UNKNOWN')
    candidate_df['registry_code'] = candidate_df['registry_code'].fillna('UNKNOWN')

    source_df = candidate_df[candidate_df['registry_code'].isin(['VCS', 'GLD'])].copy()
    cdm_df = candidate_df[candidate_df['registry_code'] == 'CDM'].copy()

    if source_df.empty or cdm_df.empty:
        print('No potential duplicate projects found between Verra/Gold Standard and CDM.')
        return candidate_df.copy()

    source_df = source_df.rename(columns={
        'Project ID': 'Source Project ID',
        'Project Name': 'Source Project Name',
        'registry_code': 'Source Registry',
    })

    cdm_df = cdm_df.rename(columns={
        'Project ID': 'CDM Project ID',
        'Project Name': 'CDM Project Name',
        'registry_code': 'CDM Registry',
        'Country': 'CDM Country',
        'Methodology 1': 'CDM Methodology 1',
        'Methodology 2': 'CDM Methodology 2',
        'Methodology 3': 'CDM Methodology 3',
        'Methodology 4': 'CDM Methodology 4',
    })

    source_key_series = source_df[['Source Project Name'] + key_cols].astype(str).apply(tuple, axis=1)
    cdm_key_series = cdm_df[['CDM Project Name', 'CDM Country', 'CDM Methodology 1', 'CDM Methodology 2', 'CDM Methodology 3', 'CDM Methodology 4']].astype(str).apply(tuple, axis=1)

    duplicate_keys = set(source_key_series).intersection(set(cdm_key_series))

    matched_source_ids = set(
        source_df.loc[source_key_series.isin(duplicate_keys), 'Source Project ID']
    )

    filtered_df = candidate_df[~candidate_df['Project ID'].isin(matched_source_ids)].copy()

    if filtered_df.equals(candidate_df):
        print('No potential duplicate projects found between Verra/Gold Standard and CDM.')
        return filtered_df

    print(f"WARNING: {len(matched_source_ids)} Verra/Gold Standard project(s) removed as duplicates matched to CDM. See warning_log.txt at the end of the run.")
    add_warning_entry(
        'Removed duplicate Verra/Gold Standard projects matched to CDM:',
        candidate_df[candidate_df['Project ID'].isin(matched_source_ids)][
            ['Project ID', 'Project Name', 'Country',
             'Methodology 1', 'Methodology 2', 'Methodology 3', 'Methodology 4',
             'registry_code']
        ]
    )
    print('\n')

    return filtered_df