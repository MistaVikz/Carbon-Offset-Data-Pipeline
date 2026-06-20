import os
import requests
import argparse
import pandas as pd

# File/URL addresses
VERRA_FILE = 'project data\\verra_projects.csv'
GOLD_FILE = 'project data\\gold_projects.csv'
CDM_FILE = 'project data\\cdm_projects.xlsx'
CDM_URL = 'https://www.iges.or.jp/en/publication_documents/pub/data/en/643/IGES_CDM_DB_v13.7_20250226.xlsx'

# Cookies used for Verra API Request.
VERRA_COOKIES = {
    "ASPSESSIONIDSEBRTARC": "JNIICHMANPKHCBEAAJLDBOMP",
    "ASPSESSIONIDSGCSRBTC": "GDEDCDJBCNJMCNGOIGKJHEKJ",
    "ASPSESSIONIDCWDQQBRB": "FMKNOKCDOOLCFONAKPLMALPA",
    "ASPSESSIONIDSEQDASRD": "BLACAKIBMEJBLCNFPJBPAKEB",
    "ASPSESSIONIDSGSCATRD": "AOGFNNKCJGCCMIDMGOGBELFG",
    }

# Headers used for Verra API request.
VERRA_HEADERS = {
    "User-Agent": "Carbon Offset Data Pipeline",
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/json",
    "Origin": "https://registry.verra.org",
    "Connection": "keep-alive",
    "Referer": "https://registry.verra.org/app/search/VCS?programType=ISSUANCE&exactResId=2939",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    }

# Headers used for Gold Standard API request.
GOLD_HEADERS = {
    "User-Agent": "Carbon Offset Data Pipeline",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Origin": "https://registry.goldstandard.org",
    "Connection": "keep-alive",
    "Referer": "https://registry.goldstandard.org/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    }

def download_verra_projects(output_file):
    """
    Downloads all Verra project data into a CSV file.

    Parameters
    ----------
    output_file : str
        The name of the output file for the download.
    
    Returns
    -------
    None

    """
    json_data = {
        "program": "VCS",
    }
    response = requests.post(
        f"https://registry.verra.org/uiapi/resource/resource/search?$skip=0&count=true&$format=csv&$exportFileName={os.path.basename(output_file)}",
        cookies=VERRA_COOKIES,
        headers=VERRA_HEADERS,
        json=json_data,
    )
    
    with open(output_file, "wb") as outfile:
        outfile.write(response.content)

def download_gold_projects():   
    """
    Downloads all Gold Standard project data into a JSON file.

    Returns
    -------
    list
        All downloaded project records.
    """
    items = []
    page = 1
    while True:
        try:
            params = {"query": "", "page": page, "size": 200}
            
            response = requests.get("https://public-api.goldstandard.org/projects", 
                                    params=params, headers=GOLD_HEADERS)
            data = response.json()
            if not data:
                break
            items.extend(data)
            if len(data) < 25:
                break
            page += 1

        except Exception as e:
            print(e)
            break

    return items

def download_cdm_projects(output_file):
    """
    Downloads the CDM Excel Database.

    Parameters
    ----------
    output_file : str
        The name of the output file for the download.
    
    Returns
    -------
    None

    """
    try:
        resp = requests.get(CDM_URL)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print("CDM Download failed. Check https://www.iges.or.jp/en/pub/iges-cdm-project-database/en for file name changes.")
        raise SystemExit(err)
    
    with open(output_file, 'wb') as output:
        output.write(resp.content)

def update_and_load_verra_data(download=True, encode='utf-8'):
    """
    Update the Verra Project data from the API, if required, then load. Default is True.

    Parameters
    ----------
    download : bool
        True = Download from the API, then use updated verra_projects.csv. False = Use 
        verra_projects.csv without downloading.
    encode : str
        Encoding to open the CSV file. Default = 'utf-8'
    
    Returns
    -------
    pandas.DataFrame
        The loaded project data.
    """ 
    # Update verra project file
    if download:
        print('Updating Verra Projects.')
        download_verra_projects(VERRA_FILE)
    else:
        print(f'Loading Verra Projects from {VERRA_FILE} without updating.')
    
    # Load verra projects
    try:
        proj_df = pd.read_csv(f'{VERRA_FILE}', encoding='utf-8')
    except FileNotFoundError:
        print(f"Error: '{VERRA_FILE}' not found in the data folder.") 
    
    return proj_df

def update_and_load_gold_data(download=True):
    """
    Download Gold Standard projects (optional), update the master CSV, and return it.

    If `download` is True this function calls `download_gold_projects()` to fetch
    the current API project list, normalizes the records to the columns
    ["name","country","gsid","developer","project_type","methodology","size","estimated_annual_credits"],
    updates matching rows in `project data/gold_projects.csv` by `gsid`, appends any new GSIDs,
    writes the updated CSV back to `project data/gold_projects.csv`, and prints counts of
    updated and added records.

    Parameters
    ----------
    download : bool
        If True, fetch data from the API before updating the CSV. If False, the function
        simply loads and returns the existing CSV.

    Returns
    -------
    pandas.DataFrame
        DataFrame loaded from `project data/gold_projects.csv` after the update (or as-is
        when `download=False`).
    """
    # Columns to download from the API
    cols = [
        "name",
        "country",
        "gsid",
        "developer",
        "project_type",
        "methodology",
        "size",
        "estimated_annual_credits",
    ]

    # Update the Gold Standard data from the API
    if download:
        print("Updating Gold Standard Projects.")
        projects = download_gold_projects()

        api_rows = []
        for p in projects:
            try:
                api_rows.append({
                    "gsid": str(p["id"]).strip(),
                    "name": p["name"] or "",
                    "developer": p["project_developer"] or "",
                    "country": p["country"] or "",
                    "project_type": p["type"] or "",
                    "methodology": p["methodology"] or "",
                    "size": p["size"] or "",
                    "estimated_annual_credits": p["estimated_annual_credits"] or 0,
                })
            except TypeError:
                continue
        api_df = pd.DataFrame.from_records(api_rows)

        api_df = api_df[[c for c in cols if c in api_df.columns]].copy()
        api_df["estimated_annual_credits"] = (
            pd.to_numeric(
                api_df["estimated_annual_credits"]
                .fillna(0)
                .astype(str)
                .str.replace(",", ""),
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        try:
            master_df = pd.read_csv(GOLD_FILE, dtype=str)
        except FileNotFoundError:
            master_df = pd.DataFrame(columns=cols)

        for c in cols:
            if c not in master_df.columns:
                master_df[c] = ""

        master_df["gsid"] = master_df["gsid"].astype(str).str.strip()
        master_df["estimated_annual_credits"] = (
            pd.to_numeric(
                master_df["estimated_annual_credits"]
                .fillna("0")
                .astype(str)
                .str.replace(",", ""),
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        master_idx = master_df.set_index("gsid")
        api_idx = api_df.set_index("gsid")
        existing_ids = set(master_idx.index)
        api_ids = set(api_idx.index)
        updated_count = len(existing_ids & api_ids)
        new_count = len(api_ids - existing_ids)

        master_idx.update(api_idx)

        if new_count:
            master_idx = pd.concat([master_idx, api_idx.loc[sorted(api_ids - existing_ids)]])

        updated_df = master_idx.reset_index()[cols]
        updated_df.to_csv(GOLD_FILE, index=False)

        print(f"{updated_count} existing projects updated, {new_count} new projects added.")

    else:
        print(f"Loading Gold Standard Projects from {GOLD_FILE} without updating.")

    try:
        proj_df = pd.read_csv(GOLD_FILE)
    except FileNotFoundError:
        print(f"Error: '{GOLD_FILE}' not found in the data folder.")
        
    return proj_df

def update_and_load_cdm_data(download=False, sheet='Sheet1', skip=0):
    """
    Download the CDM Project datatase, if required, then load.

    Parameters
    ----------
    download : bool
        True = Download the database, then open cdm_projects.xlsx. False = Use 
        cdm_projects.xlsx without downloading. Default is False.
    sheet : str
        Sheet name for data extration. Default = 'Sheet1'
    skip : int
        Number of rows to skip. Default =0
    
    Returns
    -------
    pandas.DataFrame
        The loaded project data.
    """
    # Download and update the CDM project data
    if download:
        print('Updating CDM Projects.')
        download_cdm_projects(CDM_FILE)
    else:
        print(f'Loading CDM Projects from {CDM_FILE} without updating.')

    # Load CDM projects
    try:
        proj_df = pd.read_excel(f'{CDM_FILE}', sheet_name=sheet, skiprows=skip)
    except FileNotFoundError:
        print(f"Error: '{CDM_FILE}' not found in the project data folder.")

    return proj_df

def create_master_gold_csv(input_path, output_path="project data/gold_projects.csv"):
    """
    Create a normalized master Gold Standard CSV from a raw CSV input.

    Reads `input_path`, renames source columns to the canonical names:
    "name","country","gsid","developer","project_type","methodology","size","estimated_annual_credits",
    trims `gsid`, coerces `estimated_annual_credits` to integer (commas removed), and
    writes the result to `output_path` if provided.

    Parameters
    ----------
    input_path : str
        Path to the original CSV export to normalize.
    output_path : str, optional
        Destination path for the normalized CSV (default "project data/gold_projects.csv").

    Returns
    -------
    pandas.DataFrame
        The normalized DataFrame (also written to `output_path` when provided).
    """
    try:
        df = pd.read_csv(input_path, dtype=str)
    except:
        f"Error: '{input_path}' not found in the project data folder."
    
    df = df.rename(columns={
        "Project Name": "name",
        "Country": "country",
        "GSID": "gsid",
        "Project Developer Name": "developer",
        "Project Type": "project_type",
        "Methodology": "methodology",
        "Size": "size",
        "Estimated Annual Credits": "estimated_annual_credits",
    })
    cols = ["name", "country", "gsid", "developer", "project_type", "methodology", "size", "estimated_annual_credits"]
    df = df[[c for c in cols if c in df.columns]].copy()
    df["gsid"] = df["gsid"].astype(str).str.strip()
    df["methodology"] = df.get("methodology").astype(object)
    df["estimated_annual_credits"] = (
        pd.to_numeric(df["estimated_annual_credits"].fillna("0").astype(str).str.replace(",", ""), errors="coerce")
        .fillna(0)
        .astype(int)
    )
    if output_path:
        df.to_csv(output_path, index=False)
    return df

def parse_args():
    """
    Parse command line arguments for turn ON Verra and Gold Standard downloads, for turning ON
    CDM download, and for creating a new master Gold Standard project CSV. WARNING: This overwrites 
    the current data in project data/gold_projects.csv).

    Returns:
        args: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--verra_off', dest='verra', action='store_false', help='Disable Verra updates')
    parser.add_argument('--gold_off',  dest='gold',  action='store_false', help='Disable Gold updates')    
    parser.add_argument('--cdm_on', dest='cdm', action='store_true', help='Enable CDM updates')
    parser.set_defaults(verra=True, gold=True, cdm=False)
    parser.add_argument('--create_master_gold', type=str, default=None, 
                        help='Create master Gold CSV from input CSV file path.')
    
    return parser.parse_args()

def print_unique_methodologies(df, cols=['Methodology 1', 'Methodology 2', 'Methodology 3', 'Methodology 4']):
    """
    Prints/Returns a list of unique Methodology Names in the dataframe. Used for
    Debugging.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe with Methodology columns.
    registry_code : cols
        List of Methodology Columns. Methodology 1, Methodology 2, Methodology 3,
        Methodology 4 as default values.

    Returns
    -------
    unique: list
        A list of unique Methodology Names.
    """
    vals = df[cols].fillna('').astype(str).values.ravel()
    uniques = {v.strip() for v in vals if v.strip()}
    for name in sorted(uniques):
        print(name)
    return uniques