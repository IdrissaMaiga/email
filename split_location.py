import pandas as pd

# Load the CSV file
df = pd.read_csv("data.csv")

# Ensure the column exists
if 'prospect_location' not in df.columns:
    raise ValueError("The column 'prospect_location' does not exist in the CSV file.")

# Split into two columns: city and country
df[['prospect_location_city', 'prospect_location_country']] = (
    df['prospect_location']
    .astype(str)
    .str.split(',', n=1, expand=True)
)

# Remove extra spaces from both columns
df['prospect_location_city'] = df['prospect_location_city'].str.strip()
df['prospect_location_country'] = df['prospect_location_country'].str.strip()

# Save the updated CSV
df.to_csv("data_with_city_country.csv", index=False)

print("✅ File saved as data_with_city_country.csv")
