import os
import sys
import argparse
from PIL import Image
import numpy as np
import struct

class SteganographyTool:
    def __init__(self):
        self.delimiter = b'END_OF_FILE'
    
    def hide_data(self, cover_image_path, secret_file_path, output_path):
        """Hide the secret file inside the image using LSB steganography."""
        try:
            # Open the image
            img = Image.open(cover_image_path)
            width, height = img.size
            
            # Convert image to numpy array
            array = np.array(list(img.getdata()))
            
            # Determine the number of channels in the image (RGB or RGBA)
            if len(img.getbands()) == 4:  # RGBA
                n_channels = 4
                flatten_img = array.flatten()
            elif len(img.getbands()) == 3:  # RGB
                n_channels = 3
                flatten_img = array.flatten()
            else:
                raise ValueError("Unsupported image format. Please use RGB or RGBA images.")
                
            # Calculate the maximum bytes that can be encoded
            n_pixels = width * height
            max_bytes = n_pixels * n_channels // 8
            
            # Read the secret file
            with open(secret_file_path, 'rb') as f:
                secret_data = f.read()
            
            # Add the file extension to the secret data for extraction later
            file_ext = os.path.splitext(secret_file_path)[1].encode()
            # Encode file extension length as 2 bytes
            ext_len_bytes = struct.pack('>H', len(file_ext))
            
            # Prepare data to hide: [ext_len][extension][data][delimiter]
            data_to_hide = ext_len_bytes + file_ext + secret_data + self.delimiter
            
            # Check if the file to hide is too large
            if len(data_to_hide) > max_bytes:
                raise ValueError(f"File too large to hide. Max size: {max_bytes} bytes")
            
            # Convert data to binary
            binary_data = ''.join(format(byte, '08b') for byte in data_to_hide)
            
            # Replace LSB of each byte in the image with our data bits
            data_index = 0
            for i in range(len(flatten_img)):
                if data_index < len(binary_data):
                    # Replace the least significant bit
                    flatten_img[i] = (flatten_img[i] & ~1) | int(binary_data[data_index])
                    data_index += 1
                else:
                    break
            
            # Reshape the array to original shape
            if n_channels == 4:
                array = flatten_img.reshape(n_pixels, 4)
            else:
                array = flatten_img.reshape(n_pixels, 3)
            
            # Convert back to image
            result = Image.fromarray(array.reshape(height, width, n_channels).astype(np.uint8))
            
            # Save the new image
            result.save(output_path)
            
            print(f"Data hidden successfully in {output_path}")
            print(f"Hidden data size: {len(data_to_hide)} bytes")
            
            return True
        
        except Exception as e:
            print(f"Error hiding data: {e}")
            return False
    
    def extract_data(self, stego_image_path, output_folder):
        """Extract the hidden data from the stego image."""
        try:
            # Open the stego image
            img = Image.open(stego_image_path)
            
            # Convert image to numpy array
            array = np.array(list(img.getdata()))
            
            # Determine the number of channels in the image
            if len(img.getbands()) == 4:  # RGBA
                n_channels = 4
                flatten_img = array.flatten()
            elif len(img.getbands()) == 3:  # RGB
                n_channels = 3
                flatten_img = array.flatten()
            else:
                raise ValueError("Unsupported image format. Please use RGB or RGBA images.")
            
            # Extract LSB from each byte to reconstruct the hidden data
            extracted_bits = ""
            for i in range(len(flatten_img)):
                extracted_bits += str(flatten_img[i] & 1)
            
            # Convert bits to bytes
            extracted_bytes = bytearray()
            for i in range(0, len(extracted_bits), 8):
                if i + 8 <= len(extracted_bits):
                    byte = int(extracted_bits[i:i+8], 2)
                    extracted_bytes.append(byte)
            
            # First 2 bytes represent the extension length
            ext_len = struct.unpack('>H', extracted_bytes[:2])[0]
            
            # Extract the file extension
            file_ext = extracted_bytes[2:2+ext_len].decode()
            
            # Extract the data after the extension
            data_start = 2 + ext_len
            
            # Find the delimiter in the extracted data
            delimiter_pos = extracted_bytes.find(self.delimiter, data_start)
            if delimiter_pos == -1:
                raise ValueError("Could not find the delimiter. The file might be corrupted.")
            
            # Extract the actual file data
            file_data = extracted_bytes[data_start:delimiter_pos]
            
            # Create the output folder if it doesn't exist
            os.makedirs(output_folder, exist_ok=True)
            
            # Generate a unique output filename
            base_name = "extracted"
            output_file = os.path.join(output_folder, f"{base_name}{file_ext}")
            counter = 1
            while os.path.exists(output_file):
                output_file = os.path.join(output_folder, f"{base_name}_{counter}{file_ext}")
                counter += 1
            
            # Write the extracted data to the output file
            with open(output_file, 'wb') as f:
                f.write(file_data)
            
            print(f"Data extracted successfully to {output_file}")
            print(f"Extracted data size: {len(file_data)} bytes")
            
            return output_file
        
        except Exception as e:
            print(f"Error extracting data: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Steganography tool to hide files in images')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Hide command
    hide_parser = subparsers.add_parser('hide', help='Hide a file in an image')
    hide_parser.add_argument('-i', '--image', required=True, help='Cover image path')
    hide_parser.add_argument('-f', '--file', required=True, help='Secret file to hide')
    hide_parser.add_argument('-o', '--output', required=True, help='Output stego image path')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract hidden data from an image')
    extract_parser.add_argument('-i', '--image', required=True, help='Stego image path')
    extract_parser.add_argument('-o', '--output', default='output', help='Output folder for extracted file')
    
    args = parser.parse_args()
    
    steg = SteganographyTool()
    
    if args.command == 'hide':
        steg.hide_data(args.image, args.file, args.output)
    elif args.command == 'extract':
        steg.extract_data(args.image, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
