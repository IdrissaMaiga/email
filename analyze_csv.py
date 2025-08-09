import pandas as pd

# Load the CSV file
df = pd.read_csv('data.csv', on_bad_lines='skip')

print('All columns:')
for i, col in enumerate(df.columns):
    print(f'{i+1:2d}. {col}')

print('\nLooking for prospect_location:')
print('prospect_location' in df.columns)

print('\nFirst few rows of location-related columns:')
location_cols = [col for col in df.columns if 'location' in col.lower()]
for col in location_cols:
    print(f'\n{col}:')
    print(df[col].head())
