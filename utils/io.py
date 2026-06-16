import json
import os
import requests
import pandas as pd
from dataclasses import dataclass, asdict

# File/URL addresses
VERRA_FILE = 'project data\\verra_projects.csv'
GOLD_FILE = 'project data\\gold_projects.json'
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
    page = 0
    while True:
        try:
            params = {
                "query": "",
                "page": page,
                "size": "100",
                "sortColumn": "",
                "sortDirection": "",
            }

            response = requests.get(
                "https://public-api.goldstandard.org/projects",
                params=params,
                headers=GOLD_HEADERS,
            )
            response.raise_for_status()

            _items = response.json()
            if not _items:
                break

            items.extend(_items)

            if len(_items) < 100:
                break

            page += 1

        except Exception as e:
            print(e)
            break

    with open(GOLD_FILE, "w") as outfile:
        json.dump(items, outfile)

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

def load_verra_data(download=True, encode='utf-8'):
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

@dataclass
class GoldProject:
    """A normalized gold standard project"""
    name: str = ""
    country: str = ""
    gsid: str = ""
    developer: str = ""
    project_type: str = ""
    methodology: str = ""
    size: str = ""
    estimated_annual_credits: float = 0
    
    dict = asdict

def load_gold_data(download=True):
    """
    Load Gold Standard data from the API or a local file.

    Parameters
    ----------
    download : bool
        True = Download from the API. False = Use gold_projects.json. Default is True.
    Returns
    -------
    pandas.DataFrame
        The loaded project data.
    """
    proj_list = []
    
    if download:
        print("Updating Gold Standard Projects.")
        projects = download_gold_projects()
    else:
        print(f'Loading Gold Standard Projects from {GOLD_FILE} without updating.')
        with open(GOLD_FILE, "r") as infile:
            projects = json.load(infile)

    for p in projects:
        try:
            project = GoldProject (
                gsid = p['id'],
                name = p['name'],
                developer = p['project_developer'],
                project_type = p['type'],
                methodology= p['methodology'],
                country = p['country'],
                size = p['size'],
                estimated_annual_credits=p['estimated_annual_credits']
                    )
            proj_list.append(project.dict())
        except TypeError:
            continue

    proj_df = pd.DataFrame.from_records(proj_list)

    # Test
    proj_df.to_csv('test_gold.csv')

    return proj_df

def load_cdm_data(download=False, sheet='Sheet1', skip=0):
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

    
    

