import os
import math
import argparse
from PIL import Image

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def hide(file_path, image_path, output_path):
    file_bytes = _read_file_bytes(file_path)
    validate_file_size(file_bytes)
    
    ext = os.path.splitext(file_path)[1][1:]
    ext_bytes = ext.encode('utf-8')
    
    size_info = _get_size_info(file_bytes, ext_bytes)
    payload = size_info + ext_bytes + file_bytes
    
    img = Image.open(image_path)
    image = _prepare_image(img, payload)
    
    encoded_image = _embed_data_in_image(image, payload)
    encoded_image.save(output_path)

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

# Utility functions

def _read_file_bytes(path):
    with open(path, "rb") as f:
        return f.read()

def validate_file_size(data):
    if len(data) > MAX_FILE_SIZE:
        raise ValueError("File too large to embed.")

def _get_size_info(file_bytes, ext_bytes):
    size_bits = format(len(file_bytes), '032b')
    ext_size_bits = format(len(ext_bytes), '032b')
    return _bits_to_bytes(size_bits + ext_size_bits)

def _prepare_image(img, payload):
    img = img.convert("RGB")
    required_pixels = math.ceil(len(payload) * 8 / 3)
    if img.width * img.height < required_pixels:
        raise ValueError("Image not large enough to hold the data.")
    return img

def _embed_data_in_image(image, data):
    flat_data_bits = ''.join(format(byte, '08b') for byte in data)
    pixels = list(image.getdata())
    
    new_pixels = []
    bit_index = 0
    last_progress = -1  # Track the last progress percentage
    
    for idx, pixel in enumerate(pixels):
        new_pixel = []
        for channel in pixel[:3]:  # R, G, B
            if bit_index < len(flat_data_bits):
                channel = (channel & ~1) | int(flat_data_bits[bit_index])
                bit_index += 1
            new_pixel.append(channel)
        
        new_pixels.append(tuple(new_pixel + list(pixel[3:])))  # Handle alpha if exists
        
        # Calculate the progress percentage
        percent = (idx + 1) / len(pixels) * 100
        percent = int(percent // 5 * 5)  # Round to nearest multiple of 5
        
        # Print progress only if the percentage has moved by 5%
        if percent > last_progress:
            _print_progress(idx + 1, len(pixels), "Embedding data in image", percent)
            last_progress = percent
    
    image.putdata(new_pixels)
    return image

def _get_lsb_bits(pixel):
    return ''.join(str(channel & 1) for channel in pixel[:3])  # R, G, B

def _parse_sizes(bits):
    size = int(bits[:32], 2)
    ext_size = int(bits[32:64], 2)
    return size, ext_size

def _bits_to_bytes(bits):
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))

def _print_progress(current, total, task_name, percent):
    bar_length = 50
    block = int(round(bar_length * percent / 100))
    progress = f"\r{task_name}: [{'#' * block}{'-' * (bar_length - block)}] {percent:.2f}%"
    print(progress, end='')

# Main method for command-line execution

def main():
    parser = argparse.ArgumentParser(description="Hide and extract files using LSB steganography.")
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Hide command
    hide_parser = subparsers.add_parser('hide', help="Hide a file inside an image.")
    hide_parser.add_argument('-f', '--file', required=True, help="The file to hide.")
    hide_parser.add_argument('-i', '--image', required=True, help="The image to embed the file into.")
    hide_parser.add_argument('-o', '--output', required=True, help="The output image with the hidden file.")
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help="Extract a hidden file from an image.")
    extract_parser.add_argument('-i', '--image', required=True, help="The image with the hidden file.")
    extract_parser.add_argument('-o', '--output_folder', required=True, help="The folder to save the extracted file.")
    
    args = parser.parse_args()

    if args.command == 'hide':
        hide(args.file, args.image, args.output)
    elif args.command == 'extract':
        extract(args.image, args.output_folder)
    else:
        print("Invalid command. Use --help for usage information.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        main()
    else:
        # Launch GUI if no CLI arguments are provided
        import tkinter as tk
        from tkinter import filedialog, messagebox

        def run_hide():
            file = filedialog.askopenfilename(title="Select File to Hide")
            image = filedialog.askopenfilename(title="Select Cover Image")
            output = filedialog.asksaveasfilename(title="Save Output Image As", defaultextension=".png")

            if not file or not image or not output:
                return

            try:
                hide(file, image, output)
                messagebox.showinfo("Success", "File successfully hidden in image!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def run_extract():
            image = filedialog.askopenfilename(title="Select Image with Hidden File")
            output_folder = filedialog.askdirectory(title="Select Folder to Save Extracted File")

            if not image or not output_folder:
                return

            try:
                extract(image, output_folder)
                messagebox.showinfo("Success", "File successfully extracted!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        root = tk.Tk()
        root.title("Steganography Tool")

        tk.Button(root, text="Hide File in Image", width=30, command=run_hide).pack(pady=10)
        tk.Button(root, text="Extract File from Image", width=30, command=run_extract).pack(pady=10)

        root.mainloop()

