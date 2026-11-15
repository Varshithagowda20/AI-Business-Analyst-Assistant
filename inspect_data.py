
import csv

# Open our sales dataset
with open("data/sales_data.csv", "r", encoding="utf-8") as file:

    # Read the CSV file
    reader = csv.DictReader(file)

    # Display column names
    print("Dataset Columns:")
    print(reader.fieldnames)

    print("\nFirst 5 Sales Records:")

    # Display first 5 records
    for i, row in enumerate(reader):
        if i == 5:
            break

        print(row)

