import os
import sys
import subprocess

# ------------------------------------------------------------
# Helper: Convert a single margin value (e.g., "5mm", "0.2in", "10pt", "12")
# into PDF points (1 inch = 72 points, 1 mm ≈ 2.8346 points).
# ------------------------------------------------------------
def to_points(value):
    """
    Convert a margin string to points.
    Supported formats:
        "5mm"   -> millimeters
        "0.2in" -> inches
        "10pt"  -> points
        "10"    -> points (default)
    """
    value = value.strip().lower()

    # mm → points
    if value.endswith("mm"):
        num = float(value[:-2])
        return num * 2.83464567

    # inches → points
    if value.endswith("in"):
        num = float(value[:-2])
        return num * 72.0

    # points explicitly
    if value.endswith("pt"):
        return float(value[:-2])

    # plain number → assume points
    return float(value)


# ------------------------------------------------------------
# Helper: Convert a margin string like:
#   "5mm"
#   "10"
#   "5mm 10mm 5mm 10mm"
# into a list of point values as strings.
# ------------------------------------------------------------
def convert_margin_string(margin_str):
    parts = margin_str.split()
    return [str(to_points(p)) for p in parts]


# ------------------------------------------------------------
# Main batch cropping function
# ------------------------------------------------------------
def batch_crop_pdfs(input_folder="pdfs",
                    output_folder="processed_pdfs",
                    margin=None):
    """
    Batch-crop all PDF files in input_folder using pdf-crop-margins.
    Output is written to output_folder.

    Parameters:
        margin (str or None):
            Optional margin string.
            Examples:
                "10"                 -> 10 pt
                "5mm"                -> 5 millimeters
                "0.2in"              -> 0.2 inches
                "5mm 10mm 5mm 10mm"  -> left, bottom, right, top
                None                 -> no extra margin
    """

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Process each PDF in the input folder
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".pdf"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)

            print(f"Cropping: {filename}")

            # Base command:
            # -p 0  → remove all detected margins (like pdfcrop)
            # -o    → specify output file
            cmd = ["pdf-crop-margins", "-p", "0", "-o", output_path]

            # If a margin is provided, convert it to points
            if margin is not None:
                margin_values = convert_margin_string(margin)

                # One margin value → use -a
                if len(margin_values) == 1:
                    cmd.extend(["-a", margin_values[0]])

                # Four margin values → use -a4 (left, bottom, right, top)
                elif len(margin_values) == 4:
                    cmd.extend(["-a4"] + margin_values)

                else:
                    raise ValueError("Margin must be 1 value or 4 values.")

            # Add the input PDF file
            cmd.append(input_path)

            # Run the cropping command
            subprocess.run(cmd, check=True)

    print("Done! All PDFs processed.")


# ------------------------------------------------------------
# Command-line entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    # Usage examples:
    #   python3 batch_crop.py
    #   python3 batch_crop.py 10
    #   python3 batch_crop.py 5mm
    #   python3 batch_crop.py "5mm 10mm 5mm 10mm"
    margin = sys.argv[1] if len(sys.argv) > 1 else None
    batch_crop_pdfs(margin=margin)
