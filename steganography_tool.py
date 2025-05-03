import os
import sys
import argparse
from PIL import Image
import numpy as np
import struct

class SteganographyTool:
    def __init__(self):
        self.delimiter = b'END_OF_FILE'
    
    def calculate_capacity(self, image_path):
        """Calculate the maximum capacity of an image for hiding data."""
        try:
            img = Image.open(image_path)
            width, height = img.size
            n_channels = len(img.getbands())
            
            if n_channels not in [3, 4]:
                raise ValueError("Unsupported image format. Please use RGB or RGBA images.")
            
            # Calculate max bytes (accounting for overhead)
            n_pixels = width * height
            total_bits = n_pixels * n_channels
            max_bytes = total_bits // 8
            
            # Account for overhead (extension length, delimiter)
            overhead = 2 + len(self.delimiter)  # 2 bytes for ext length + delimiter
            usable_bytes = max_bytes - overhead
            
            return {
                'width': width,
                'height': height,
                'pixels': n_pixels,
                'channels': n_channels,
                'total_bits': total_bits,
                'max_bytes': max_bytes,
                'usable_bytes': usable_bytes,
                'format': img.format,
                'mode': img.mode
            }
        except Exception as e:
            print(f"Error calculating image capacity: {e}")
            return None

    def hide_data(self, cover_image_path, secret_file_path, output_path):
        """Hide the secret file inside the image using LSB steganography."""
        try:
            # Calculate capacity first
            capacity = self.calculate_capacity(cover_image_path)
            if not capacity:
                return False
                
            # Open the image
            img = Image.open(cover_image_path)
            width, height = img.size
            n_channels = capacity['channels']
            
            # Important warning for JPEG images
            if img.format == 'JPEG':
                print("WARNING: JPEG is a lossy format and may corrupt the hidden data when saved.")
                print("Consider using PNG or BMP for more reliable steganography.")
            
            # Convert image to numpy array
            array = np.array(list(img.getdata()))
            flatten_img = array.flatten()
                
            # Read the secret file
            with open(secret_file_path, 'rb') as f:
                secret_data = f.read()
            
            # Get file size information
            secret_file_size = len(secret_data)
            
            # Add the file extension to the secret data for extraction later
            file_ext = os.path.splitext(secret_file_path)[1].encode()
            # Encode file extension length as 2 bytes
            ext_len_bytes = struct.pack('>H', len(file_ext))
            
            # Prepare data to hide: [ext_len][extension][data][delimiter]
            data_to_hide = ext_len_bytes + file_ext + secret_data + self.delimiter
            
            # Check if the file to hide is too large
            if len(data_to_hide) > capacity['max_bytes']:
                print("\nERROR: File too large for this image")
                print(f"File size to hide: {len(data_to_hide)} bytes")
                print(f"Image capacity: {capacity['max_bytes']} bytes")
                print(f"Difference: {len(data_to_hide) - capacity['max_bytes']} bytes too large\n")
                print("Options:")
                print("1. Use a larger image")
                print("2. Compress your data before hiding it")
                print("3. Split your data across multiple images")
                return False
            
            # Convert data to binary
            binary_data = ''.join(format(byte, '08b') for byte in data_to_hide)
            
            # Display progress information
            total_bits = len(binary_data)
            total_capacity_bits = capacity['total_bits']
            print(f"Image dimensions: {width}x{height} ({capacity['pixels']} pixels)")
            print(f"Image format: {img.format}, Mode: {img.mode}")
            print(f"Using {total_bits} of {total_capacity_bits} available bits ({(total_bits/total_capacity_bits)*100:.2f}% of capacity)")
            
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
                array = flatten_img.reshape(capacity['pixels'], 4)
            else:
                array = flatten_img.reshape(capacity['pixels'], 3)
            
            # Convert back to image
            result = Image.fromarray(array.reshape(height, width, n_channels).astype(np.uint8))
            
            # Save the new image - ensure we're using a lossless format for the output
            output_ext = os.path.splitext(output_path)[1].lower()
            if output_ext == '.jpg' or output_ext == '.jpeg':
                print("Warning: Converting output to PNG to prevent data loss")
                output_path = os.path.splitext(output_path)[0] + '.png'
            
            result.save(output_path)
            
            print(f"\nData hidden successfully in {output_path}")
            print(f"Hidden data size: {len(data_to_hide)} bytes ({secret_file_size} bytes of actual file data)")
            
            return True
        
        except Exception as e:
            print(f"Error hiding data: {e}")
            return False
    
    def extract_data(self, stego_image_path, output_folder):
        """Extract the hidden data from the stego image."""
        try:
            # Open the stego image
            img = Image.open(stego_image_path)
            width, height = img.size
            
            print(f"Opening stego image: {stego_image_path}")
            print(f"Image dimensions: {width}x{height}")
            print(f"Image mode: {img.mode}")
            
            # Convert image to numpy array
            array = np.array(list(img.getdata()))
            
            # Determine the number of channels in the image
            n_channels = len(img.getbands())
            print(f"Number of channels: {n_channels}")
            
            if n_channels not in [3, 4]:
                raise ValueError("Unsupported image format. Please use RGB or RGBA images.")
            
            flatten_img = array.flatten()
            print(f"Total pixels to process: {len(array)}")
            print(f"Total values to extract from: {len(flatten_img)}")
            
            # Extract LSB from each byte to reconstruct the hidden data
            print("Extracting bits from image...")
            extracted_bits = ""
            for i in range(len(flatten_img)):
                extracted_bits += str(flatten_img[i] & 1)
                
                # Print progress periodically
                if i % 1000000 == 0 and i > 0:
                    print(f"Processed {i:,}/{len(flatten_img):,} values ({i/len(flatten_img)*100:.2f}%)")
            
            print("Converting bits to bytes...")
            # Convert bits to bytes
            extracted_bytes = bytearray()
            for i in range(0, len(extracted_bits), 8):
                if i + 8 <= len(extracted_bits):
                    byte = int(extracted_bits[i:i+8], 2)
                    extracted_bytes.append(byte)
            
            print(f"Total extracted bytes: {len(extracted_bytes)}")
            
            # Debug: Check if the delimiter exists in the extracted data
            delimiter_exists = self.delimiter in extracted_bytes
            print(f"Delimiter exists in data: {delimiter_exists}")
            if delimiter_exists:
                first_occurrence = extracted_bytes.find(self.delimiter)
                print(f"First occurrence of delimiter at byte: {first_occurrence}")
            
            # First 2 bytes represent the extension length
            if len(extracted_bytes) < 2:
                raise ValueError("Extracted data is too short, doesn't even contain extension length.")
                
            ext_len = struct.unpack('>H', extracted_bytes[:2])[0]
            print(f"Extension length: {ext_len} bytes")
            
            if ext_len > 10:  # Reasonable upper limit for an extension
                print("WARNING: Extension length seems unusually large. Possible data corruption.")
            
            # Extract the file extension
            if len(extracted_bytes) < 2 + ext_len:
                raise ValueError(f"Extracted data is too short to contain the full extension.")
                
            file_ext = extracted_bytes[2:2+ext_len].decode('utf-8', errors='replace')
            print(f"Detected file extension: {file_ext}")
            
            # Extract the data after the extension
            data_start = 2 + ext_len
            
            # Find the delimiter in the extracted data
            delimiter_pos = extracted_bytes.find(self.delimiter, data_start)
            
            if delimiter_pos == -1:
                print("WARNING: Could not find the delimiter. The file might be corrupted or incomplete.")
                print("Trying to process all available data...")
                file_data = extracted_bytes[data_start:]
            else:
                print(f"Found delimiter at position {delimiter_pos}")
                # Extract the actual file data
                file_data = extracted_bytes[data_start:delimiter_pos]
            
            print(f"Extracted file data size: {len(file_data)} bytes")
            
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
            
            # Debug: Check the beginning of the file data
            try:
                preview_size = min(100, len(file_data))
                if file_ext.lower() in ['.txt', '.py', '.java', '.js', '.html', '.css', '.json', '.xml', '.md']:
                    print("\nPreview of extracted data:")
                    print(file_data[:preview_size].decode('utf-8', errors='replace'))
                    print("..." if len(file_data) > preview_size else "")
            except:
                pass
            
            return output_file
        
        except Exception as e:
            print(f"Error extracting data: {e}")
            import traceback
            traceback.print_exc()
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
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze an image capacity')
    analyze_parser.add_argument('-i', '--image', required=True, help='Image to analyze')
    
    args = parser.parse_args()
    
    steg = SteganographyTool()
    
    if args.command == 'hide':
        steg.hide_data(args.image, args.file, args.output)
    elif args.command == 'extract':
        steg.extract_data(args.image, args.output)
    elif args.command == 'analyze':
        capacity = steg.calculate_capacity(args.image)
        if capacity:
            print("\nImage Capacity Analysis:")
            print(f"Dimensions: {capacity['width']}x{capacity['height']} ({capacity['pixels']} pixels)")
            print(f"Format: {capacity['format']}, Mode: {capacity['mode']} ({capacity['channels']} channels)")
            print(f"Maximum data capacity: {capacity['max_bytes']} bytes ({capacity['max_bytes']/1024:.2f} KB)")
            print(f"Usable data capacity: {capacity['usable_bytes']} bytes ({capacity['usable_bytes']/1024:.2f} KB)")
            
            if capacity['format'] == 'JPEG':
                print("\nWARNING: JPEG is a lossy format and may corrupt the hidden data.")
                print("For steganography, PNG or BMP formats are recommended.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
