import pandas as pd
pd.options.display.max_columns = 5
from offsets_db_data.data import catalog

def main():
    
    print(catalog['projects'].describe())
    print(catalog['credits'].describe())

if __name__ == "__main__":
    main()