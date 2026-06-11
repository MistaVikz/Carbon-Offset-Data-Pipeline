import json
import re
from pathlib import Path
from utils.processing import *

# Mapping JSON file locations
TECH_MAPPING_FILE = Path(__file__).resolve().parent / 'project_type_mappings.json'  # CURRENTLY DISABLED
COUNTRY_MAPPING_FILE = Path(__file__).resolve().parent / 'ISO3166_country_mapping.json'

# ------------------------------- PROJECT TYPES CURRENTLY DISABLED -------------------------------------
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
    
# Load the technology mapping data
_MAPPINGS_DATA = _load_mappings_data(TECH_MAPPING_FILE)

# Substring match rules: category -> set(keywords)
SUBSTRING_MATCHES = {
    category: set(values)
    for category, values in _MAPPINGS_DATA.get('SubstringMatches', {}).items()
}

# Exact lookup table: category -> registry -> set(labels)
PROJECT_TYPE_LOOKUP = {
    category: {registry: set(values) for registry, values in registry_map.items()}
    for category, registry_map in _MAPPINGS_DATA.items()
    if category not in ('KnownCommaLabels', 'SubstringMatches')
}

# Known comma-containing labels to preserve as single tokens: registry -> set(labels)
KNOWN_COMMA_LABELS = {
    registry: set(labels)
    for registry, labels in _MAPPINGS_DATA.get('KnownCommaLabels', {}).items()
}

# Technologies are processed in a specific order to ensure consistent categorization when multiple matches occur
CATEGORY_ORDER = [
    'Renewable Energy',
    'Energy Efficiency',
    'Waste & Methane',
    'Transportation',
    'AFOLU',
    'Industrial / Manufacturing',
]

def _split_project_type(project_type, registry_code):
    """
    Split `project_type` into normalized parts while preserving known comma labels
    specific to `registry_code`.
    """
    normalized = str(project_type).strip().lower()
    if normalized in KNOWN_COMMA_LABELS.get(registry_code, set()):
        return [normalized]
    return [part.strip() for part in re.split(r';\s*|\s*,\s*', normalized) if part.strip()]

def standardize_technologies(project_type, registry_code):
    """
    Standardize a raw `project_type` to a canonical category.

    Priority:
      1) Substring matches from JSON (e.g., Biogas/Biomass keywords)
      2) Exact registry-specific matches from PROJECT_TYPE_LOOKUP
      3) Return original `project_type` if no match
    """
    if pd.isna(project_type):
        return project_type

    parts = _split_project_type(project_type, registry_code)

    # 1) Substring matches (keyword-based)
    for category, keywords in SUBSTRING_MATCHES.items():
        if any(keyword in part for part in parts for keyword in keywords):
            return category

    # 2) Exact registry-specific matches (ordered by CATEGORY_ORDER)
    for category in CATEGORY_ORDER:
        lookup = PROJECT_TYPE_LOOKUP.get(category, {})
        if any(part in lookup.get(registry_code, set()) for part in parts):
            return category

    return project_type
# ----------------------------------------------------------------------------------------------------

# Load the country mapping data
COUNTRY_MAPPING = _load_mappings_data(COUNTRY_MAPPING_FILE)

def normalize_country_label(label):
    """
    Normalize a country label for lookup.

    Converts the input to a lowercase string, trims whitespace,
    and normalizes apostrophe-like characters to a single apostrophe.
    """
    return re.sub(r"[`´’]", "'", str(label).strip()).lower()

def _build_country_lookup():
    """
    Build a flat lookup dictionary from the country mapping JSON.

    Returns a dict mapping normalized country labels and aliases to
    a canonical ISO country name. The lookup includes:
      - canonical names themselves
      - any alias labels listed under each canonical entry
    """
    lookup = {}
    for canonical, registry_map in COUNTRY_MAPPING.items():
        lookup[normalize_country_label(canonical)] = canonical
        if isinstance(registry_map, dict):
            for labels in registry_map.values():
                for label in labels:
                    if label:
                        lookup[normalize_country_label(label)] = canonical
        elif isinstance(registry_map, list):
            for label in registry_map:
                if label:
                    lookup[normalize_country_label(label)] = canonical
    return lookup

COUNTRY_LOOKUP = _build_country_lookup()

def standardize_countries(proj_df, country_col='Country'):
    """
    Standardize a column in a project DataFrame that Contains Country Names.

    Parameters
    ----------
    proj_df : pandas.DataFrame
        Project metadata containing a country name column.

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
        
        normalized = normalize_country_label(value)
        
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
    
def standardize_methodologies(proj_df, registry_code):
    """
    Standardize the `Methodology` field for different registries.

    Parameters
    ----------
    proj_df : pandas.DataFrame
        Project metadata. May include columns `'Methodology'`, `'Methodology1'`..`'Methodology4'`.
    registry_code : str
        Registry code to guide normalization. Expected values: `'VCS'`, `'GLD'`, `'CDM'`.

    Returns
    -------
    pandas.DataFrame
        A copy of `proj_df` with a normalized `Methodology` column:
        - `'VCS'`: remove periods, trim whitespace, fill missing with `'Not Provided'`, append `';'`.
        - `'GLD'`: for values starting with `'A'` keep only the first token; otherwise set to `'Other'`; then keep text before the first period, normalize blanks to `'Not Provided'`, append `';'`.
        - `'CDM'`: combine non-empty `Methodology1`..`Methodology4` into a single `'; '`-separated string with trailing `';'`; if all empty, set `'Not Provided'`.
    """
    proj_df = proj_df.copy()

    if registry_code == 'VCS':
        proj_df['Methodology'] = proj_df['Methodology'].fillna('Not Provided')
        proj_df['Methodology'] = proj_df['Methodology'].str.replace('.', '').str.strip()
        proj_df['Methodology'] = proj_df['Methodology'] + ';'
    
    elif registry_code == 'GLD':
        proj_df['Methodology'] = proj_df['Methodology'].fillna('')

        # For methodologies starting with 'A', keep only the first part (e.g., 'ACM0018', 'AM0022', etc.)
        mask = proj_df['Methodology'].str.startswith('A')
        proj_df.loc[mask, 'Methodology'] = proj_df.loc[mask, 'Methodology'].str.split(n=1).str[0]

        # Set methodologies that aren't compatible with Verra to 'Other'
        gs_mask = (~mask) & (proj_df['Methodology'].astype(str).str.upper() != 'NOT PROVIDED')
        proj_df.loc[gs_mask, 'Methodology'] = 'Other'

        proj_df['Methodology'] = proj_df['Methodology'].astype(str).str.partition('.')[0].str.strip()
        proj_df['Methodology'] = proj_df['Methodology'].replace({'': 'Not Provided;', 'nan': 'Not Provided'})
        proj_df['Methodology'] = proj_df['Methodology'].replace({'Not provided': 'Not Provided'})
        proj_df['Methodology'] = proj_df['Methodology'] + ';'
    
    elif registry_code == 'CDM':
        def _combine_methods(row):
            cols = ['Methodology1', 'Methodology2', 'Methodology3', 'Methodology4']
            parts = [str(row[c]).strip() for c in cols if pd.notna(row.get(c)) and str(row.get(c)).strip() != '']
            return 'Not Provided' if not parts else '; '.join(parts) + ';'

        proj_df['Methodology'] = proj_df.apply(_combine_methods, axis=1)
        proj_df['Methodology'] = proj_df['Methodology'].fillna('Not Provided;')
        proj_df['Methodology'] = proj_df['Methodology'].str.replace('.', '').str.strip()

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

def standardize_proponents(proj_df, prop_col = 'Proponent'):
    """
    Normalize and clean a column with Proponent Data in a projects DataFrame.

    Parameters
    - proj_df (pd.DataFrame): DataFrame expected to contain a `Proponent` column.

    Behavior
    1. Replace connector characters (e.g. '&' -> ' and ') and strip punctuation.
    2. Convert values to string and lower-case them.
    3. Collapse multiple whitespace runs to a single space and trim ends.
    4. Mark multi-entity cells (containing `\n` or `;`) as 'multiple proponents'.
    5. Convert obvious empty tokens ('', 'nan', 'none', 'n/a') to `pd.NA` and drop those rows.

    Returns
    - pd.DataFrame:
        A copy of `proj_df` with a cleaned `Proponent` column.
    """
    proj_df = proj_df.copy()
    if prop_col not in proj_df.columns:
        return proj_df

    def _multiple_proponents(value):
        if pd.isna(value):
            return value

        text = str(value).strip()
        if text == '':
            return pd.NA

        if '\n' in text or ';' in text:
            return 'multiple proponents'
        return text
    
    def _remove_suffixes(text):
        suffixes = [
            ' ltd', ' limited', ' inc', ' incorporated', ' corp', ' corporation',
            ' co', ' gmbh', ' sarl', ' sa', ' plc', ' llc', ' pvt ltd', ' pty ltd',
            ' ag', ' nv', ' bv', ' se', ' ltda'
        ]
        
        if pd.isna(text):
            return text
        
        text = text.strip()
        for suffix in suffixes:
            if text.endswith(suffix):
                return text[: -len(suffix)].strip()
        return text

    # Normalize case/punctuation/whitespace
    proj_df[prop_col] = proj_df[prop_col].str.replace('  ',' ')
    proj_df[prop_col] = proj_df[prop_col].str.replace('.','')
    proj_df[prop_col] = proj_df[prop_col].str.replace(',','')
    proj_df[prop_col] = proj_df[prop_col].str.replace('&','')
    proj_df[prop_col] = proj_df[prop_col].str.replace('-','')
    proj_df[prop_col] = proj_df[prop_col].str.lower().str.strip()

    # Remove suffixes
    proj_df[prop_col] = proj_df[prop_col].apply(_remove_suffixes)

    # Combine multple proponents
    proj_df[prop_col] = proj_df[prop_col].apply(_multiple_proponents)
    
    # Drop rows with no proponent (Additional Proponent set to None)
    if prop_col == 'Additional Proponents':
        proj_df.fillna({'Additional Proponents' : 'None'}, inplace=True)
    else:
        proj_df.dropna(subset=[prop_col], inplace=True)
    return proj_df
