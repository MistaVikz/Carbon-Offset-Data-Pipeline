import json
import re
from pathlib import Path
import pandas as pd

# Mapping JSON file locations
COUNTRY_MAPPING_FILE = Path(__file__).resolve().parent / 'ISO3166_country_mapping.json'
METHODOLOGY_MAPPING_FILE = Path(__file__).resolve().parent / 'methodology_mapping.json'

def _load_mappings_data(MAPPING_FILE):
    """
    Load a JSON mapping file.

    Parameters
    ----------
    MAPPING_FILE : pathlib.Path
        Path to the JSON file containing mapping definitions.

    Returns
    -------
    dict
        Parsed JSON data from the mapping file.
    """
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def normalize_label(label):
    """
    Normalize a label for lookup.

    Converts the input to a lowercase string, trims whitespace,
    and normalizes apostrophe-like characters to a single apostrophe.
    """
    return re.sub(r"[`´’]", "'", str(label).strip()).lower()

def _build_lookup(MAPPING):
    """
    Build a flat lookup dictionary from a mapping JSON file.

    Returns a dict mapping normalized labels and aliases to
    a canonical name. The lookup includes:
      - canonical names themselves
      - any alias labels listed under each canonical entry
    """
    lookup = {}
    for canonical, registry_map in MAPPING.items():
        lookup[normalize_label(canonical)] = canonical
        if isinstance(registry_map, dict):
            for labels in registry_map.values():
                for label in labels:
                    if label:
                        lookup[normalize_label(label)] = canonical
        elif isinstance(registry_map, list):
            for label in registry_map:
                if label:
                    lookup[normalize_label(label)] = canonical
    return lookup

# Load the country lookup
COUNTRY_MAPPING = _load_mappings_data(COUNTRY_MAPPING_FILE)
COUNTRY_LOOKUP = _build_lookup(COUNTRY_MAPPING)

def standardize_countries(proj_df, country_col='Country'):
    """
    Standardize a column in a project DataFrame that Contains Country Names.

    Parameters
    ----------
    proj_df : pandas.DataFrame
        Dataframe countaining project data.
    country_col : Column containing country name data.
        
    Returns
    -------
    pandas.DataFrame
        A copy of proj_df where country name values are normalized to
        canonical ISO country names based on the JSON mapping file.
        Unmapped values are left unchanged, blank strings become pd.NA,
        and non-country values are converted to pd.NA. Blank values are dropped
        only when the function is used on the "Country" column.
        'Multiple countries' and No 'Additional Countries' are allowed for the 
        'Other Involved Countries' column 
    """
    proj_df = proj_df.copy()
    if country_col not in proj_df.columns:
        return proj_df

    def _normalize_country(country):
        # Define values that indicate missing or non-specific country information
        not_provided_values = {'international', 'n/a', 'na', 'not provided', 'unknown', 'tbd', 'eu'}
        
        if pd.isna(country):
            return country
        
        # Allow multiple countries in 'Other Countries Involed'
        if country_col == 'Other Countries Involved':
            if ';' in country or '\n' in country or ',' in country or 'or' in country:
                return 'Multiple Additional Countries'

        value = str(country).strip()
        if value == '':
            return pd.NA
        
        normalized = normalize_label(value)
        
        # Remove non-country labels
        if normalized in not_provided_values:
            return pd.NA

        return COUNTRY_LOOKUP.get(normalized, value)

    proj_df[country_col] = proj_df[country_col].apply(_normalize_country)
    
    # Blanks are dropped for 'Country' but not for 'Other Countries Involved'
    if country_col == 'Country':
        proj_df = proj_df.dropna(subset=[country_col])
    else:
        proj_df = proj_df.fillna({country_col: 'No Additional Countries'})
    
    return proj_df

# Load the methodology lookup
METHODOLOGY_MAPPING = _load_mappings_data(METHODOLOGY_MAPPING_FILE)
METHODOLOGY_LOOKUP = _build_lookup(METHODOLOGY_MAPPING)

def standardize_methodology(proj_df, meth_col = 'Methodology 1'):
    """
    Standardize a column in a project DataFrame that contains methodology names.

    Parameters
    ----------
    proj_df : pandas.DataFrame
        Dataframe countaining project data.
    meth_col : Column containing methodology names.
        
    Returns
    -------
    pandas.DataFrame
        A copy of proj_df where methodology name values are normalized to
        canonical Verra/Gold Standard/CDM methodology names based on the JSON mapping file. 
    """
    proj_df = proj_df.copy()
    if meth_col not in proj_df.columns:
        return proj_df

    def _normalize_methodology(methodology):
        
        if pd.isna(methodology):
            return methodology
        
        value = str(methodology).strip()
        
        # Set methodologies with no information to <NA>
        if value == '' or value == 'Not Provided':
            return pd.NA
        
        normalized = normalize_label(value)
              
        return METHODOLOGY_LOOKUP.get(normalized, value)

    proj_df[meth_col] = proj_df[meth_col].apply(_normalize_methodology)
    
    # Drop <NA> in Methodology 1
    if meth_col == 'Methodology 1':
        proj_df = proj_df.dropna(subset=[meth_col])

    return proj_df

def standardize_project_size(proj_df):
    """
    Normalize the Project Size column to LARGE, SMALL, or MICRO.

    Parameters
    ----------
    proj_df : pandas.DataFrame
        Project metadata containing a 'Project Size' column.
    
    Returns
    -------
    pandas.DataFrame
        A copy of proj_df with normalized 'Project Size' values.
        Unrecognized and blank/missing values become 'UNKNOWN'.
    """
    proj_df = proj_df.copy()
    if 'Project Size' not in proj_df.columns:
        return proj_df

    size_map = {
        'large scale': 'LARGE',
        'large-scale': 'LARGE',
        'large': 'LARGE',
        'small scale': 'SMALL',
        'small-scale': 'SMALL',
        'small': 'SMALL',
        'micro scale': 'MICRO',
        'micro-scale': 'MICRO',
        'micro': 'MICRO',
    }

    def _normalize_size(size):
        if pd.isna(size):
            return 'UNKNOWN'

        value = str(size).strip()
        if value == '':
            return 'UNKNOWN'

        normalized = re.sub(r'[\s_-]+', ' ', value.lower())
        return size_map.get(normalized, 'UNKNOWN')

    proj_df['Project Size'] = proj_df['Project Size'].apply(_normalize_size)
    return proj_df

def standardize_analysis(proj_df, inv_col = 'Investment Analysis Option'):
    """
    Normalize and clean a column with Analysis Data in a projects DataFrame.

    Parameters
    - proj_df (pd.DataFrame): DataFrame.
    - prop_col: column with Analysis data

    Returns
    - pd.DataFrame:
        A copy of `proj_df` with a cleaned Analysis column.
    """
    proj_df = proj_df.copy()

    proj_df.fillna({inv_col:'None'}, inplace=True)
    proj_df[inv_col] = proj_df[inv_col].str.replace('none', 'None')
    proj_df[inv_col] = proj_df[inv_col].str.replace('\n',' & ')
    proj_df[inv_col] = proj_df[inv_col].str.replace('  ',' ')

    return proj_df
