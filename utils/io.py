import json
import os
import requests
import pandas as pd
from dataclasses import dataclass, asdict

# File/URL addresses
GOLD_FILE = 'project data\\gold_projects.json'
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

def load_file_data(filename, type, sheet='Sheet1', skip = 0, encode='utf-8'):
    """
    Load project data from either a CSV or Excel file in the project data folder.

    Parameters
    ----------
    filename : str
        The name of the file to load.
    type : str
        File type, either `"Excel"` or `"CSV"`.
    sheet : str, optional
        Excel sheet name to read when `type == "Excel"`. Defaults to `'Sheet1'`.
    skip : int, optional
        Number of rows to skip when reading an Excel sheet. Defaults to `0`.
    encode : str, optional
        Text encoding to use when reading CSV files. Defaults to `'utf-8'`.

    Returns
    -------
    pandas.DataFrame
        The loaded project data.
    """
    if type == "Excel":
        try:
            proj_df = pd.read_excel(f'{filename}', sheet_name=sheet, skiprows=skip)
        except FileNotFoundError:
            print(f"Error: '{filename}' not found in the project data folder.")    
    else:
        try:
            proj_df = pd.read_csv(f'{filename}', encoding=encode)
        except FileNotFoundError:
            print(f"Error: '{filename}' not found in the data folder.")    
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
        True = Download from the API. False = Use gold_projects.json
    Returns
    -------
    pandas.DataFrame
        The loaded project data.
    """
    proj_list = []
    
    if download:
        print("Downloading Gold Projects.")
        projects = download_gold_projects()
    else:
        print(f'Loading Gold Projects from {GOLD_FILE} ')
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

