import os
import math
from PIL import Image

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

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
