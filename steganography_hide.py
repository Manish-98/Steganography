import os
from PIL import Image
from steganography_utils import _read_file_bytes, validate_file_size, _get_size_info, _prepare_image, _embed_data_in_image, _print_progress

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

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hide a file inside an image.")
    parser.add_argument('-f', '--file', required=True, help="The file to hide.")
    parser.add_argument('-i', '--image', required=True, help="The image to embed the file into.")
    parser.add_argument('-o', '--output', required=True, help="The output image with the hidden file.")
    
    args = parser.parse_args()
    hide(args.file, args.image, args.output)
