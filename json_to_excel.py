import json
import pandas as pd

def export_json_to_excel(json_file_or_data, output_filename="output.xlsx", priority_fields=None):
    """
    Reads a JSON file, extracts unique fields, and exports data to an Excel file.
    :param json_file: Path to the input JSON file
    :param output_filename: Path to the output Excel file
    :param priority_fields: List of fields to appear first in the Excel file
    """
    try:
        # Load JSON data from file
        if isinstance(json_file_or_data, str):
            with open(json_file_or_data, "r", encoding="utf-8") as file:
                json_data = json.load(file)


            if not isinstance(json_data, list):
                raise ValueError("JSON file must contain a list of objects.")
        else:
            json_data = json_file_or_data

        all_keys = set()
        for entry in json_data:
            all_keys.update(entry.keys())

        # Ensure priority fields appear first
        priority_fields = priority_fields or []
        remaining_fields = sorted(all_keys - set(priority_fields))  # Sort remaining fields

        # Final ordered field list
        ordered_fields = priority_fields + remaining_fields

        # Convert JSON data to a consistent format
        formatted_data = [
            {key: ", ".join(map(str, entry[key])) if isinstance(entry.get(key, None), list) else entry.get(key, None)
            for key in ordered_fields}
            for entry in json_data if len(list(entry.keys())) > 1
        ]

        # Create a DataFrame and export to Excel
        df = pd.DataFrame(formatted_data)
        df.columns = [col.replace('_', ' ').title() for col in df.columns]

        df.to_excel(output_filename, index=False)

        print(f"✅ Data exported successfully to {output_filename}")

    except Exception as e:
        print(f"❌ Error: {e}")

# Example Usage
if __name__ == "__main__":
    input_json_file = "RiverRaidd.json"  # Change this to your JSON file path
    output_excel_file = "excels/RiverRaid.xlsx"  # Change output filename if needed
    priority_columns = ["console", "title", "comments", "mobyid", "country", "Genre", 'rating', 'description', 'published_by', 'developed_by']  # Fields to always appear first
    export_json_to_excel(input_json_file, output_excel_file, priority_columns)
