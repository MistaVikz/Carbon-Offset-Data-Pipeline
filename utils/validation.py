def compare_estimated_and_issued(df, estimated_col, actual_col):
    # Thresholds to trigger warnings
    ACTUAL_THRESHOLD = 50.
    EQUAL_THRESHOLD = 5.

    actual_greater_than_estimated = df[df[actual_col] > df[estimated_col]]
    actual_equal_to_estimated = df[df[actual_col] == df[estimated_col]]

    actual_greater_than_estimate_per = len(actual_greater_than_estimated) / len(df) * 100
    actual_equal_to_estimate_per = len(actual_equal_to_estimated) / len(df) * 100

    if(actual_greater_than_estimate_per > ACTUAL_THRESHOLD):
        print(f"WARNING: {actual_greater_than_estimate_per:.2f}% of projects have Actual Emission Reductions exceed the Estimated Emission Reductions.")

    if(actual_equal_to_estimate_per > EQUAL_THRESHOLD):
        print(f"WARNING: {actual_equal_to_estimate_per:.2f}% of projects have Actual Emission Reductions equal the Estimated Emission Reductions.")

def check_estimated_with_no_issued(df, estimated_col, actual_col):
    missing_estimated = df[(df[estimated_col] == 0) & (df[actual_col] > 0)]
    missing_actual = df[(df[estimated_col] > 0) & (df[actual_col] == 0)]
    
    if(len(missing_estimated) > 0):
        print(f"WARNING: {len(missing_estimated) / len(df) * 100:.2f}% of projects have no Estimated Emission Reductions but have Actual Emission Reductions.")
        print(missing_estimated[['Project ID', 'Project Name', 'Estimated Emission Reductions', 'Actual Emission Reductions']])

    if(len(missing_actual) >0 ):
        print(f"WARNING: {len(missing_actual) / len(df) * 100:.2f}% of projects have Estimated Emission Reductions but no Actual Emission Reductions.")
        print(missing_actual[['Project ID', 'Project Name', 'Estimated Emission Reductions', 'Actual Emission Reductions']])