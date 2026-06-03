def check_for_missing_projects(proj_df, issued_df, registry_code, project_id_col='Project ID', issued_id_col='numeric_id'):
    """
    Check for projects with issued credits that are missing from the project dataset and print details.
    Parameters
    - proj_df (pd.DataFrame): DataFrame containing project data, expected to include a column with project IDs.
    - issued_df (pd.DataFrame): DataFrame containing issued credit summaries, expected to include a column with project IDs.
    - registry_code (str): Registry code to include in the warning message.
    - project_id_col (str): Column name in proj_df that contains project IDs (default 'ID').
    - issued_id_col (str): Column name in issued_df that contains project IDs (default 'numeric_id').
    
    Behavior
    - Identifies projects that have issued credits (in issued_df) but are missing from the project dataset (proj_df).
    - If any such projects are found, prints a warning count and displays the subset of issued_df with those projects,
      showing the project ID and actual emission reductions.
    """
    missing_proj = issued_df[~issued_df[issued_id_col].isin(proj_df[project_id_col])]
    if len(missing_proj) > 0:
        print(f"WARNING: {len(missing_proj)} project(s) with issued credits in registry {registry_code} are missing from the project dataset.")
        print(missing_proj[['numeric_id', 'Actual Emission Reductions']])
    
def compare_estimated_and_actual(df, estimated_col, actual_col, ACTUAL_THRESHOLD=50., EQUAL_THRESHOLD=10.):
    """
    Compare estimated vs actual emission reductions and print summary warnings.

    Parameters
    - df (pd.DataFrame): DataFrame containing project rows.
    - estimated_col (str): Column name for estimated emission reductions.
    - actual_col (str): Column name for actual emission reductions.

    Behavior
    - Computes the percentage of projects where actual > estimated and where actual == estimated.
    - Prints a warning if percentage of actual > estimated exceeds an internal threshold,
      and another warning if percentage of actual == estimated exceeds a separate threshold.
    """

    actual_greater_than_estimated = df[df[actual_col] > df[estimated_col]]
    actual_equal_to_estimated = df[df[actual_col] == df[estimated_col]]

    actual_greater_than_estimate_per = len(actual_greater_than_estimated) / len(df) * 100
    actual_equal_to_estimate_per = len(actual_equal_to_estimated) / len(df) * 100

    if(actual_greater_than_estimate_per > ACTUAL_THRESHOLD):
        print(f"WARNING: {actual_greater_than_estimate_per:.2f}% of projects have Actual Emission Reductions exceed the Estimated Emission Reductions.")

    if(actual_equal_to_estimate_per > EQUAL_THRESHOLD):
        print(f"WARNING: {actual_equal_to_estimate_per:.2f}% of projects have Actual Emission Reductions equal the Estimated Emission Reductions.")

def check_estimated_and_actual(df, estimated_col, actual_col):
    """
    Run sanity checks on estimated and actual emission reduction values and print details.

    Parameters
    - df (pd.DataFrame): DataFrame containing project rows (expected to include 'Project ID' and 'Project Name').
    - estimated_col (str): Column name for estimated emission reductions.
    - actual_col (str): Column name for actual emission reductions.

    Behavior
    - Identifies projects with:
      - missing estimated (estimated == 0 but actual > 0)
      - missing actual (estimated > 0 but actual == 0)
      - negative estimated values
      - negative actual values
    - For each non-empty set, prints a warning count and displays the subset with
      ['Project ID', 'Project Name', estimated_col, actual_col'] columns.

    """
    missing_estimated = df[(df[estimated_col] == 0) & (df[actual_col] > 0)]
    missing_actual = df[(df[estimated_col] > 0) & (df[actual_col] == 0)]
    negative_estimated = df[df[estimated_col] < 0]
    negative_actual = df[df[actual_col] < 0]

    if(len(missing_estimated) > 0):
        print(f"WARNING: {len(missing_estimated)} project(s) has/have no Estimated Emission Reductions but have Actual Emission Reductions.")
        print(missing_estimated[['Project ID', 'Project Name', 'Estimated Emission Reductions', 'Actual Emission Reductions']])

    if(len(missing_actual) > 0):
        print(f"WARNING: {len(missing_actual)} project(s) has/have Estimated Emission Reductions but no Actual Emission Reductions.")
        print(missing_actual[['Project ID', 'Project Name', 'Estimated Emission Reductions', 'Actual Emission Reductions']])

    if(len(negative_estimated) > 0):
        print(f"WARNING: {len(negative_estimated)} project(s) has/have negative Estimated Emision Reductions.")
        print(negative_estimated[['Project ID', 'Project Name', 'Estimated Emission Reductions', 'Actual Emission Reductions']])

    if(len(negative_actual) > 0):
        print(f"WARNING: {len(negative_actual)} project(s) has/have negative Actual Emision Reductions.")
        print(negative_actual[['Project ID', 'Project Name', 'Estimated Emission Reductions', 'Actual Emission Reductions']])
