import json
from pathlib import Path
import re
from utils.processing import *

MAPPING_FILE = Path(__file__).resolve().parent / 'project_type_mappings.json'

def _load_mappings_data():
    """
    Load mapping JSON that may contain:
      - KnownCommaLabels: registry -> [labels with commas to preserve]
      - SubstringMatches: category -> [keywords]
      - other canonical categories -> registry -> [exact labels]
    """
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

_MAPPINGS_DATA = _load_mappings_data()

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

