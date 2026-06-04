import json
from pathlib import Path
import re
from utils.processing import *

MAPPING_FILE = Path(__file__).resolve().parent / 'project_type_mappings.json'

def _load_mappings_data():
    """
    Load project type mappings and known comma labels from JSON file.
    
    Returns
    -------
    dict
        Raw mapping data from 'project_type_mappings.json' containing:
        - 'KnownCommaLabels': registry-specific labels with commas that should not be split
        - Category entries: each canonical category maps registry codes to project type strings
    """
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

_MAPPINGS_DATA = _load_mappings_data()

"""Lookup table mapping canonical project types to registry-specific source labels."""
PROJECT_TYPE_LOOKUP = {
    category: {registry: set(values) for registry, values in registry_map.items()}
    for category, registry_map in _MAPPINGS_DATA.items()
    if category != 'KnownCommaLabels'
}

"""Registry-specific project type labels containing commas that should not be split. """
KNOWN_COMMA_LABELS = {
    registry: set(labels)
    for registry, labels in _MAPPINGS_DATA.get('KnownCommaLabels', {}).items()
}

def _split_project_type(project_type, registry_code):
    """
    Split a project type string into individual components while preserving known comma labels.
    
    Parameters
    ----------
    project_type : str
        Raw project type string, possibly containing multiple categories separated by `;` or `,`.
    registry_code : str
        Registry code ('VCS', 'GLD', or 'CDM') to determine which comma labels to preserve.
    
    Returns
    -------
    list of str
        Normalized, whitespace-trimmed components. Labels in KNOWN_COMMA_LABELS are
        returned as single items; others are split on `;` and `,` separators.
        
    Examples
    --------
    >>> _split_project_type('Wind power, PV', 'CDM')
    ['wind power', 'pv']
    
    >>> _split_project_type('Fugitive emissions from fuels (solid, oil and gas)', 'VCS')
    ['fugitive emissions from fuels (solid, oil and gas)']
    """
    normalized = str(project_type).strip().lower()
    if normalized in KNOWN_COMMA_LABELS.get(registry_code, set()):
        return [normalized]
    return [part.strip() for part in re.split(r';\s*|\s*,\s*', normalized) if part.strip()]

def standardize_technologies(project_type, registry_code):
    """
    Standardize a project type to a canonical category.
    
    Applies normalization rules in the following priority order:
    1. Biogas (keyword match on 'biogas')
    2. Biomass (keyword match on 'biomass', 'biofuel', or 'biofuels')
    3. Renewable Energy, Energy Efficiency, Waste & Methane, Transportation, AFOLU,
       Industrial / Manufacturing (exact match from PROJECT_TYPE_LOOKUP)
    4. Return unchanged if no match found
    
    Parameters
    ----------
    project_type : str or NaN
        Raw project type from source registry data.
    registry_code : str
        Registry code ('VCS', 'GLD', or 'CDM') to determine applicable mappings.
    
    Returns
    -------
    str
        Canonical project type category or the original project_type if no mapping
        is found. Returns NaN unchanged.
        
    Examples
    --------
    >>> standardize_technologies('wind', 'GLD')
    'Renewable Energy'
    
    >>> standardize_technologies('Biogas - Heat', 'GLD')
    'Biogas'
    """
    if pd.isna(project_type):
        return project_type

    parts = _split_project_type(project_type, registry_code)

    if any('biogas' in part for part in parts):
        return 'Biogas'

    if any('biomass' in part or 'biofuel' in part or 'biofuels' in part for part in parts):
        return 'Biomass'

    for category in [
        'Renewable Energy',
        'Energy Efficiency',
        'Waste & Methane',
        'Transportation',
        'AFOLU',
        'Industrial / Manufacturing',
    ]:
        lookup = PROJECT_TYPE_LOOKUP.get(category, {})
        if any(part in lookup.get(registry_code, set()) for part in parts):
            return category

    return project_type

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

