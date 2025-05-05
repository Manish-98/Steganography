import os
from PIL import Image
from steganography_utils import _get_lsb_bits, _parse_sizes, _bits_to_bytes, _print_progress

def extract(image_path, output_folder):
    image = Image.open(image_path).convert("RGB")
    pixels = list(image.getdata())
    
    flat_bits = ''
    total_pixels = len(pixels)
    last_progress = -1  # Track the last progress percentage for extraction
    
    # Track progress while extracting bits from the image pixels
    for idx, pixel in enumerate(pixels):
        flat_bits += _get_lsb_bits(pixel)
        
        # Calculate the progress percentage for extraction
        percent = (idx + 1) / total_pixels * 100
        percent = int(percent // 5 * 5)  # Round to nearest multiple of 5
        
        # Print progress only if the percentage has moved by 5%
        if percent > last_progress:
            _print_progress(idx + 1, total_pixels, "Extracting hidden data", percent)
            last_progress = percent
    
    size, ext_size = _parse_sizes(flat_bits)
    
    ext = _bits_to_bytes(flat_bits[64:64 + (ext_size * 8)]).decode('utf-8')
    file_data = _bits_to_bytes(flat_bits[64 + (ext_size * 8):64 + (ext_size * 8) + (size * 8)])
    
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, f"extracted_file.{ext}")
    
    # Write the extracted file without a progress bar
    with open(output_path, "wb") as f:
        f.write(file_data)

    # Finalize extraction progress to 100% once the extraction is complete
    _print_progress(total_pixels, total_pixels, "Extracting hidden data", 100)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract a hidden file from an image.")
    parser.add_argument('-i', '--image', required=True, help="The image with the hidden file.")
    parser.add_argument('-o', '--output_folder', required=True, help="The folder to save the extracted file.")
    
    args = parser.parse_args()
    extract(args.image, args.output_folder)
