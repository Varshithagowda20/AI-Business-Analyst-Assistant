
import csv

# Open the sales dataset
with open("data/sales_data.csv", "r", encoding="utf-8") as file:

    # Read the CSV data
    reader = csv.DictReader(file)

    # Display column names
    print("Dataset Columns:")
    print(reader.fieldnames)

    # Display first five records
    print("\nFirst 5 Sales Records:")

    for i, row in enumerate(reader):
        if i == 5:
            break

        print(row)
