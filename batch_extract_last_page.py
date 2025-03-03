# This script batch extracts the last page of each PDF file in the folder
# "pdfs" and saves them to the folder "processed_pdfs" using the pymupdf package

import os
import pymupdf

# Define the path to the subfolder containing the original PDF files
subfolder_path = 'pdfs'

# Define the path to the output folder
output_folder_path = 'processed_pdfs'

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder_path):
    os.makedirs(output_folder_path)

# Function to delete the last page of a PDF file and save it to the output folder
def save_last_page(pdf_path, output_folder):
    pdf_document = pymupdf.open(pdf_path)
    num_pages = pdf_document.page_count
    # Create the output file path
    output_file_path = os.path.join(output_folder, os.path.basename(pdf_path))
    # Select the last page
    pdf_document.select([num_pages - 1])
    # Save the updated PDF document (last page!)
    pdf_document.save(output_file_path)
    pdf_document.close()

# Walk through the directory and subdirectories
for root, dirs, files in os.walk(subfolder_path):
    for file in files:
        if file.endswith('.pdf'):
            file_path = os.path.join(root, file)
            try:
                save_last_page(file_path, output_folder_path)
                print(f'Deleted the last page of {file} and saved to {output_folder_path}')
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

print('Batch processing completed.')
