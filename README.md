# Carbon Offset Data Pipeline

A Python pipeline for collecting, cleaning, standardizing, and combining carbon offset project data from multiple registries into a unified dataset for analysis.

## Overview

This project pulls project metadata and issued credit data from several registries and prepares a consistent output dataset. It supports:

- Verra (VCS)
- Gold Standard (GLD)
- CDM

The pipeline performs data normalization for:

- country names
- methodologies
- project size categories
- emission reductions estimates and actual issuances
- duplicate project detection across registries

## What the Pipeline Does

The workflow includes:

1. Downloading or loading registry project data
2. Cleaning and standardizing project fields
3. Matching projects to issued-credit records
4. Generating registry-specific datasets
5. Producing a unified dataset across the selected registries
6. Writing warning logs for data quality issues

## Repository Structure

- main.py — entry point for running the full pipeline
- utils/io.py — file loading, downloads, argument parsing, and CSV/XLSX handling
- utils/processing.py — credit processing and dataframe merging
- utils/standards.py — country and methodology normalization logic
- utils/validation.py — data quality checks and warnings
- maps/ — mapping files for countries and methodologies
- methodologies/ — registry methodology reference files
- project data/ — project datasets used by the pipeline
- output/ — generated output artifacts
- unused data/ — archived or unused registry exports

## Requirements

This project is written in Python and expects the following libraries:

- pandas
- requests
- openpyxl

If needed, install them with:

```bash
pip install pandas requests openpyxl
```

## Setup

1. Clone the repository.
2. Open the project folder in your Python environment.
3. Install the required dependencies.
4. Ensure the data folders and mapping files are present.

## Usage

Run the pipeline with:

```bash
python main.py
```

### Common Options

The script supports flags for updating or excluding registries:

- `--verra_update_off` disables Verra updates
- `--gold_update_off` disables Gold Standard updates
- `--cdm_update_on` enables CDM updates
- `--verra_off` excludes Verra from the unified dataset
- `--gold_off` excludes Gold Standard from the unified dataset
- `--cdm_off` excludes CDM from the unified dataset
- `--cdm_only` creates a CDM-only dataset with additional fields
- `--create_master_gold <file>` creates a normalized Gold Standard master CSV from an input file

Example:

```bash
python main.py --gold_update_off --cdm_update_on --cdm_only
```

## Data Sources

The pipeline uses:

- registry project exports or API responses
- issued credit transaction data from the catalog source used by the project
- local CSV/XLSX files stored in the project data folder

## Outputs

The pipeline generates datasets and logs that are written to the output locations configured by the script.

Typical outputs include:

- unified dataset with projects from selected registries
- registry-specific project data
- warning logs for data quality issues
- exported CSV/XLSX files in the project data or output folders

## Data Quality and Validation

The pipeline includes checks for:

- missing project records for issued credits
- negative or inconsistent emission reduction values
- invalid country or methodology names
- duplicate projects across registries

Warnings are recorded and reported during execution.

## Notes

- Some registry APIs may be rate limited or return incomplete data.
- The pipeline is designed to use local project data when updates are skipped or fail.
- Data mappings may need updates as registry names or methodology conventions change over time.

## Contributing

If you plan to extend the project, the main areas to consider are:

- adding new registry support
- improving normalization logic
- refining validation checks
- expanding mapping files for countries or methodologies

## References

This project draws on the following external sources and reference material:

- OffsetDB for updated issued credit data: https://carbonplan.org/research/offsets-db
- Verra and Gold Standard request headers and cookies, adapted from the Carbon Offset Scraper project by antiboredom: https://github.com/antiboredom/carbon-offset-scraper/blob/main/README

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

See the LICENSE file for details.
