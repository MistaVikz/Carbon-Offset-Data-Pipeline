
def compare_estimated_and_issued(df, id_col, estimated_col, issued_col):
    """
    Compare estimated emission reductions against issued credits for each project.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing project records.
    id_col : str
        Name of the column with project IDs.
    estimated_col : str
        Name of the column with estimated annual emission reductions.
    issued_col : str
        Name of the column with average annual issued credits.

    Returns
    -------
    None
        Prints a summary of any projects where issued credits exceed estimated ERs.
    """
    discrepancies = df[df[issued_col] > df[estimated_col]]
    if(len(discrepancies) == 0):
        print("\nNo discrepancies found: All projects have average annual issued credits less than or equal to estimated ERs.")
    else:
        print(f"\nWARNING: Number of projects with average annual issued credits greater than estimated ERs: {len(discrepancies)}")
        print(discrepancies[[id_col, estimated_col, issued_col]])