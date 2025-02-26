# This file show how to remove the last page(s)
# in a PDF document

import pymupdf

# Open the original PDF file
pdf_document = pymupdf.open('mypdf.pdf')

# Get the total number of pages
num_pages = pdf_document.page_count

# Delete the last page
pdf_document.delete_page(num_pages - 1)

# Save the updated PDF document
pdf_document.save('mypdf_updated.pdf')

# Close the PDF document
pdf_document.close()

print(f'The last page has been deleted and the updated document has been saved as mypdf_updated.pdf')
