def compare_estimated_and_issued(df, estimated_col, issued_col):
    issued_greater_than_estimated = df[df[issued_col] > df[estimated_col]]
    issued_equal_to_estimated = df[df[issued_col] == df[estimated_col]]

    print(f"Percentage of projects where average annual issued credits exceed estimated ERs: {len(issued_greater_than_estimated) / len(df) * 100:.2f}%")
    print(f"Percentage of projects where average annual issued credits equal estimated ERs: {len(issued_equal_to_estimated) / len(df) * 100:.2f}%")

def check_estimated_with_no_issued(df, estimated_col, issued_col):
    missing_estimated = df[(df[estimated_col] == 0) & (df[issued_col] > 0)]
    missing_issued = df[(df[estimated_col] > 0) & (df[issued_col] == 0)]
    print(f"Percentage of projects with no estimated ERs but with issued credits: {len(missing_estimated) / len(df) * 100:.2f}%")
    print(f"Percentage of projects with estimated ERs but no issued credits: {len(missing_issued) / len(df) * 100:.2f}%")