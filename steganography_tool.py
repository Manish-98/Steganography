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
    
    flat_bits = ''.join(_get_lsb_bits(pixel) for pixel in pixels)
    size, ext_size = _parse_sizes(flat_bits)
    
    ext = _bits_to_bytes(flat_bits[64:64 + (ext_size * 8)]).decode('utf-8')
    file_data = _bits_to_bytes(flat_bits[64 + (ext_size * 8):64 + (ext_size * 8) + (size * 8)])
    
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, f"extracted_file.{ext}")
    with open(output_path, "wb") as f:
        f.write(file_data)


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
    
    for pixel in pixels:
        new_pixel = []
        for channel in pixel[:3]:  # R, G, B
            if bit_index < len(flat_data_bits):
                channel = (channel & ~1) | int(flat_data_bits[bit_index])
                bit_index += 1
            new_pixel.append(channel)
        new_pixels.append(tuple(new_pixel + list(pixel[3:])))  # Handle alpha if exists
    
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
    main()
