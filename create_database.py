
import pandas as pd
import sqlite3

# Read the sales CSV file
df = pd.read_csv("data/sales_data.csv")

# Connect to SQLite database
connection = sqlite3.connect("data/business.db")

# Store sales data inside the database
df.to_sql(
    "sales",
    connection,
    if_exists="replace",
    index=False
)

print("Database created successfully!")
print("Sales data stored in SQLite.")

# Close the database connection
connection.close()
