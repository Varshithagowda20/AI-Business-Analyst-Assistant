import pandas as pd
import sqlite3

# Connect to our database
connection = sqlite3.connect("data/business.db")

# Read SQL table into Pandas
df = pd.read_sql_query("SELECT * FROM sales", connection)

# Display first 5 records
print("Sales Data:")
print(df.head())

# Close connection
connection.close()