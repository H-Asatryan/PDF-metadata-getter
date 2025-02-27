import os
import pymupdf

def batch_edit_pdf_titles(input_folder, output_folder):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for filename in os.listdir(input_folder):
        if filename.endswith('.pdf'):
            input_path = os.path.join(input_folder, filename)
            output_filename = filename[:3]  # First three symbols of the old filename

            # Open the PDF file
            pdf_document = pymupdf.open(input_path)
            info = pdf_document.metadata
            title = info.get('title', '')

            # Remove last 29 characters of the PDF title
            new_title = title[:-29]

            # Set the new title in the metadata
            pdf_document.set_metadata({'title': new_title})

            # Create the new output filename and save the processed file
            new_output_filename = output_filename + new_title + '.pdf'
            output_path = os.path.join(output_folder, new_output_filename)
            pdf_document.save(output_path, garbage=4, deflate=True)
            pdf_document.close()
            print(f"Processed: {filename} -> {new_output_filename}")

if __name__ == "__main__":
    input_folder = 'pdfs'
    output_folder = 'processed_pdfs'
    batch_edit_pdf_titles(input_folder, output_folder)
