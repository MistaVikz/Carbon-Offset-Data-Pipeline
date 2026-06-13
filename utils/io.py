import json
import os
import requests

# CDM Database URL. Excel Filename might change.
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

def download_gold_projects(output_file):   
    """
    Downloads all Gold Standard project data into a JSON file.

    Parameters
    ----------
    output_file : str
        The name of the output file for the download.
    
    Returns
    -------
    None

    """
    items = []
    page = 1
    while True:
        try:
            if ((page -1 ) % 50 == 0):
                print(f'Downloading Gold Standard Projects: Page {page}...')
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

            _items = response.json()
            items += _items

            page += 1
            if len(_items) == 0:
                break
        except Exception as e:
            print(e)
            pass

    with open(output_file, "w") as outfile:
       json.dump(items, outfile)


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