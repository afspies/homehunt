#!/usr/bin/env python3
"""Test the search command's export functionality"""

import subprocess
import csv
import os

# Run a search with export
print("Running search with CSV export...")
result = subprocess.run([
    "python", "-m", "homehunt", "search", "London",
    "--min-price", "1500",
    "--max-price", "2500", 
    "--max-results", "5",
    "--output", "test_search_export.csv",
    "--no-save"  # Don't save to DB
], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)

# Check if file was created
if os.path.exists("test_search_export.csv"):
    print("\nCSV file created successfully!")
    
    # Check contents
    with open("test_search_export.csv", 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        if rows:
            print(f"\nHeader row found: {len(rows[0])} columns")
            print("Headers:", rows[0])
            print(f"Data rows: {len(rows) - 1}")
        else:
            print("\nERROR: CSV file is empty!")
else:
    print("\nERROR: CSV file was not created!")