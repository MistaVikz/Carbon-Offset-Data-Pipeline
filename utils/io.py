import os
import requests
import argparse
import datetime
import pandas as pd
from pathlib import Path

# Global variable to store warning entries
_WARNING_ENTRIES = []

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
    try:
        response = requests.post(
            f"https://registry.verra.org/uiapi/resource/resource/search?$skip=0&count=true&$format=csv&$exportFileName={os.path.basename(output_file)}",
            cookies=VERRA_COOKIES,
            headers=VERRA_HEADERS,
            json=json_data,
        )
    
        with open(output_file, "wb") as outfile:
            outfile.write(response.content)
    except Exception as e:
        print("Verra Download failed. Try again later or turn off Verra updates.")
        raise SystemExit(e)

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
            print(f"Gold Standard download failed on page {page}. Try again later or turn off Gold Standard updates.")
            raise SystemExit(e)

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
    except requests.exceptions.HTTPError as e:
        print("CDM Download failed. Try again later or turn off CDM updates.")
        raise SystemExit(e)
    
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
        print(f'Loading CDM Projects from {CDM_FILE} without updating.\n')

    # Load CDM projects
    try:
        proj_df = pd.read_excel(f'{CDM_FILE}', sheet_name=sheet, skiprows=skip)
    except FileNotFoundError:
        print(f"Error: '{CDM_FILE}' not found in the project data folder.\n")

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
    Parse command line arguments for excluding Verra, Gold Standard and/or CDM from the Unified Dataset. Also 
    arguments for turning OFF Verra and Gold Standard downloads and for turning ON CDM download. Arugments for
    creating a CDM only dataset with additional features (Default=False) and for creating a new master Gold 
    Standard project CSV. WARNING: This overwrites the current data in project data/gold_projects.csv.

    Returns:
        args: Parsed command line arguments.
    
    Behavior:
        - Registry Exclusion has a higher priority than updating. Ex: Turning ON Verra updates while excluding
        Verra will not do anything.
        - Regiistry Exclusion has a higher priority than the CDM-Only Dataset. Ex: The CDM-Only Dataset will not be
        created if CDM is excluded and CDM-Only is turned on. 
        - Excluding Verra and Gold Standard but including CDM will create a dataset with only CDM projects. However,
        it will not have the extra features in the CDM-only dataset (--cdm_only to create the CDM only dataset.) 
    """
    parser = argparse.ArgumentParser()
    
    # Update Commands
    parser.add_argument('--verra_update_off', dest='verra_update', action='store_false', help='Disable Verra updates')
    parser.add_argument('--gold_update_off',  dest='gold_update',  action='store_false', help='Disable Gold Standard updates')    
    parser.add_argument('--cdm_update_on', dest='cdm_update', action='store_true', help='Enable CDM updates')
    parser.set_defaults(verra_update=True, gold_update=True, cdm_update=False)

    # Dataset Commands
    parser.add_argument('--verra_off', dest='verra_include', action='store_false', help='Exclude Verra from the Unified Dataset')
    parser.add_argument('--gold_off',  dest='gold_include',  action='store_false', help='Exclude Gold Standard from the Unified Dataset')
    parser.add_argument('--cdm_off', dest='cdm_include', action='store_false', help='Exclude CDM from the Unified Dataset')
    parser.set_defaults(verra_include=True, gold_include=True, cdm_include=True)

    # Create CDM-only Dataset
    parser.add_argument('--cdm_only', dest='cdm_only', action = 'store_true', help = 'Create a CDM only dataset with additional features')
    parser.set_defaults(cdm_only = False)

    # Create Master Gold Project CSV
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

def reset_warning_log():
    """
    Clear any buffered warning entries.

    Returns
    -------
    None
    """
    _WARNING_ENTRIES.clear()

def add_warning_entry(message, df=None):
    """
    Store a warning message and optional dataframe for later logging.

    Parameters
    ----------
    message : str
        The warning message to store.
    df : pandas.DataFrame, optional
        An optional dataframe associated with the warning for later display.

    Returns
    -------
    None
    """
    _WARNING_ENTRIES.append((message, df))

def _format_table(df, max_width=24):
    """
    Format a dataframe as a fixed-width text table for warning logs.

    Parameters
    ----------
    df : pandas.DataFrame
        The dataframe to format for display in a text log.
    max_width : int
        Maximum width for each displayed column value. Default is 24.

    Returns
    -------
    str
        A readable fixed-width text table representation of the dataframe.
    """
    if df is None or df.empty:
        return ""

    display_df = df.copy()
    for col in display_df.columns:
        display_df[col] = display_df[col].astype(str).replace({"nan": "", "None": ""})

    widths = {
        col: min(max(len(str(col)), max(len(str(val)) for val in display_df[col])), max_width)
        for col in display_df.columns
    }

    lines = []
    header = " | ".join(str(col).ljust(widths[col]) for col in display_df.columns)
    separator = "-+-".join("-" * widths[col] for col in display_df.columns)
    lines.append(header)
    lines.append(separator)

    for _, row in display_df.iterrows():
        values = []
        for col in display_df.columns:
            value = str(row[col])
            values.append(value[:widths[col]].ljust(widths[col]))
        lines.append(" | ".join(values))

    return "\n".join(lines)

def write_warning_log(output_folder):
    """
    Write all buffered warning entries to a text log file in the output folder.

    Parameters
    ----------
    output_folder : str
        Path to the folder where the warning log should be written.

    Returns
    -------
    None
    """
    output_path = Path(output_folder) / "warning_log.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as log_file:
        if not _WARNING_ENTRIES:
            log_file.write("No warnings generated during validation.\n")
            return

        for idx, (message, df) in enumerate(_WARNING_ENTRIES, start=1):
            log_file.write(f"\n{'=' * 80}\n")
            log_file.write(f"Warning {idx}: {message}\n")
            if df is not None and not df.empty:
                log_file.write(_format_table(df))
                log_file.write("\n")
    print(f"Detailed warning information saved to {output_path}\n")        

def get_display_subset(df, columns):
    """
    Return a dataframe subset using the available display columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The dataframe to subset.
    columns : list
        Column names to include if they are available in the dataframe.

    Returns
    -------
    pandas.DataFrame
        A dataframe containing only the available display columns.
    """
    available_cols = [col for col in columns if col in df.columns]
    if available_cols:
        return df[available_cols]
    return df.copy()

def create_output_folder(include_both=False):
    """
    Create a time-stamped folder for the simulation output and summary output. Includes 
    eith -All or -UNIFIED in the directory name depending on whether all datasets or only
    the Unified dataset will be saved. 

    Parameters
    ----------
    include_both : bool
        If True, use the -ALL directory suffix. If False, use the -UNIFIED suffix (Default=False). 
    """
    # Get the current date and time
    now = datetime.datetime.now()
    date_time = now.strftime("%Y%m%d-%H%M%S")

    # Add suffix
    if include_both:
        dir_name = date_time + '-ALL'
    else:
        dir_name = date_time + '-UNIFIED'

    # Get the current directory of the script
    current_dir = os.path.dirname(__file__)

    # Construct the path to the output directory
    output_dir = os.path.join(current_dir, '..', 'output')

    # Create a new folder with the timestamp and suffix
    folder_name = os.path.join(output_dir, dir_name)
    os.makedirs(folder_name, exist_ok=True)

    return folder_name

def save_dataset(output_folder, df, is_cdm_only=False, has_verra= True, has_gold = True, 
                  has_cdm = True):
    """
    Saves either the CDM-Only or the Unified Dataset to the Output Folder. Formats the Unififed
    Dataset's filename if registries are excluded. 

    Parameters
    ----------
    output_folder : str
        Path to the folder to save the dataset.
    df : Dataframe
        The dataset to be saved.
    is_cdm_only : bool
        True if df is the CDM Only dataset (Default=False).
    has_verra : bool
        True if the Verra registry is included in the Unified dataset (Default=True).
    has_gold : bool
        True if the Gold Standard registry is included in the Unified dataset (Default=True).
    has_cdm : bool
        True if the CDM registry is included in the Unified dataset (Default=True).
    """
    if(is_cdm_only):
        # Save CDM-only Dataset 
        df.to_csv(f'{output_folder}/cdm_dataset.csv')
        print(f'\nCDM-only Dataset saved to {output_folder}/cdm_dataset.csv.')
    else:
        # Build Unified Dataset filename
        unified_output = 'unified_dataset.csv'
        if not has_cdm:
            unified_output = 'no_cdm_' + unified_output
        if not has_gold:
            unified_output = 'no_gold_' + unified_output
        if not has_verra:
            unified_output = 'no_verra_' + unified_output

        # Save Unified Dataset
        df.to_csv(f'{output_folder}/{unified_output}')
        print(f'\nUnified Dataset saved to {output_folder}/{unified_output}.')
        
    return
    