import pandas as pd
import json

# Example list of JSON objects
with open('mobygames_platforms.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Convert the list of dictionaries to a DataFrame
df = pd.DataFrame(data)

# Write to Excel
output_file = "platforms.xlsx"
df.to_excel(output_file, index=False)

print(f"Excel file '{output_file}' has been created.")
