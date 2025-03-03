# This script extracts document titles from all PDF files
# in the "pdfs" subfolder and saves the titles to a CSV file

import os
import pandas as pd
import pymupdf

# Define the path to the subfolder
subfolder_path = 'pdfs'

# Initialize a list to store the document titles
document_titles = []

# Walk through the directory and subdirectories
for root, dirs, files in os.walk(subfolder_path):
    for file in files:
        if file.endswith('.pdf'):
            file_path = os.path.join(root, file)
            try:
                # Open the PDF file
                pdf_document = pymupdf.open(file_path)
                # Activate one of the following 2 commands
                # Extract the title from the metadata
                # title = pdf_document.metadata.get('title', 'Unknown Title')
                # Extract the title from the metadata and remove last 29 characters
                title = pdf_document.metadata.get('title', 'Unknown Title')[:-29]
                document_titles.append(title)
                pdf_document.close()
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

# Define the CSV file name
output_folder = './csv'
os.makedirs(output_folder, exist_ok=True)
csv_file_name = output_folder+'/'+'document_titles.csv'

# Create a DataFrame from the list of document titles
df = pd.DataFrame(document_titles, columns=['Document Title'])

# Write the DataFrame to a CSV file
df.to_csv(csv_file_name, index=False)

print(f'Document titles have been saved to {csv_file_name}')
