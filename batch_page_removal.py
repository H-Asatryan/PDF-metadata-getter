# This file batch removes the last pages of all PDF files
# with filename prefixes listed in "prefixes.csv".
# The ne PDF files are saved to a different folder, named "processed_pdfs".
# Note that 'pymupdf' package does not allow overwriting files!

import os
import pandas as pd
import pymupdf

# Read the prefixes from the CSV file
prefixes_df = pd.read_csv('./csv/prefixes.csv', dtype=str)
prefixes = prefixes_df['prefix'].tolist()

# Define the path to the subfolder containing the original PDF files
subfolder_path = 'pdfs'

# Define the path to the output folder
output_folder_path = 'processed_pdfs'

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder_path):
    os.makedirs(output_folder_path)

# Function to delete the last page of a PDF file and save it to the output folder
def delete_last_page_and_save(pdf_path, output_folder):
    pdf_document = pymupdf.open(pdf_path)
    num_pages = pdf_document.page_count
    if num_pages > 0:
        pdf_document.delete_page(num_pages - 1)
    # Create the output file path
    output_file_path = os.path.join(output_folder, os.path.basename(pdf_path))
    pdf_document.save(output_file_path)
    pdf_document.close()

# Walk through the directory and subdirectories
for root, dirs, files in os.walk(subfolder_path):
    for file in files:
        if file.endswith('.pdf'):
            for prefix in prefixes:
                if file.startswith(prefix):
                    file_path = os.path.join(root, file)
                    try:
                        delete_last_page_and_save(file_path, output_folder_path)
                        print(f'Deleted the last page of {file} and saved to {output_folder_path}')
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")

print('Batch processing completed.')
