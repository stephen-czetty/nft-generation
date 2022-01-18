from io import BytesIO
import sys
import getpass
import json
from string import Template
from datetime import datetime
import argparse
from pathlib import Path
import hashlib

from PIL import Image
from PIL.PngImagePlugin import PngInfo
import pdf2image
from lxml import etree
import qrcode
import qrcode.image.svg
from gnupg import GPG

from .pillowhost import PillowHostElement

# TODO: Move to a factory
from .private.stenoprivate import Stenography

def open_image(file_name):
    try:
        return pdf2image.convert_from_path(file_name, dpi=600)[0]
    except IndexError:
        return None

def add_steno(image, hidden_data, password, filename):
    try:
        steno_host = PillowHostElement(image)
    except FileNotFoundError:
        pass
    steno_host.insert_message(hidden_data, bits=1, password=password, parasite_filename=filename)
    return Image.fromarray(steno_host.data)

def make_exif(description, copyright):
    exif = Image.Exif()
    exif[0x8298] = copyright
    exif[0x9286] = exif[0x010e] = description

    return exif

def save_image(image, exif, file_name):
    png_info = PngInfo()
    exif_text = f'\nexif\n{len(exif.tobytes())}\n{exif.tobytes().hex()}'
    png_info.add_text('Raw profile type exif', exif_text, zip=True)
    image.save(file_name, format='PNG', lossless=True, dpi=(600,600), pnginfo=png_info, exif=exif.tobytes(), optimize=True, minimize_size=True)

def get_qrcode_svg(data_to_encode):
    # Generating a QR code...  This seems to be about right.  Maybe need to adjust the scaling (in the template svg) on an actual signature?
    qr = qrcode.QRCode(border=1)
    qr.add_data(data_to_encode)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage, fit=True)
    return etree.tostring(img.make_path())

def get_gpg_signature(file_name, keyid):
    password = getpass.getpass('Enter passphrase for GPG private key: ')
    gpg = GPG()
    with open(file_name, 'rb') as stream:
        return gpg.sign_file(stream, detach=True, keyid=keyid, passphrase=password)

def make_certificate(output_file, gpg_signature, minted_date):
    with open('certificate-template.svg') as template:
        source = Template(template.read())
    
    with open(output_file, 'w') as output:
        substitutions = {
            'PGP_SIGNATURE': gpg_signature,
            'MINTED_DATE': minted_date,
            'ARTIST_SIGNATURE': ''
        }

        output.write(source.substitute(substitutions))

def calculate_steno_password(image):
    return hashlib.sha256(image.tobytes()).hexdigest()

def get_options():
    options_parser = argparse.ArgumentParser(description='Pre-process an image for NFT minting')
    options_parser.add_argument('source_file', type=str, help='File to process')
    options_parser.add_argument('--description', '-d', type=str, help='Description of image for EXIF data')
    options_parser.add_argument('--output', '-o', type=str, help='Base output filename (without extension)  Defaults to base name of source.')
    options_parser.add_argument('--steno-file', type=str, help='File to use for stenography. (Defaults to a scaled copy of main image.)')
    options_parser.add_argument('--steno-password', type=str, help='Password to use for stenography', dest='steno_password')
    options_parser.add_argument('--no-steno', action='store_false', dest='steno')
    options_parser.add_argument('--no-sign', action='store_false', help='Do not generate signature', dest='gpg')
    options_parser.add_argument('--no-certificate', action='store_false', help='Do not generate a certificate of authenticity', dest='certificate')
    return options_parser.parse_args(sys.argv[1:])

options = get_options()
input_filename = options.source_file
image = open_image(input_filename)
if not image:
    print('No image found, exiting.')
    sys.exit()

with open('config.json') as config_file:
    config = json.load(config_file)

description = options.description or input('Enter description of this image: ')
output_filename_base = options.output or Path(options.source_file).stem
output_filename = output_filename_base + '.png'
svg_filename = output_filename_base + '.svg'

if options.steno:
    print('Adding steno content...', end='')
    with Stenography(image, file_path=options.steno_file, steno_password=options.steno_password) as steno:
        image = steno.insert_verification_data()
        print('Done.')
        print(f'Your stenograpy password is: [{steno.steno_password}].  Save this info!')

print('Adding exif data...', end='')
exif = make_exif(description, config['copyright'])
print('Done.')

print('Saving image...', end='')
save_image(image, exif, output_filename)
print('Done.')

gpg_signature = '(No signature generated)'
if options.gpg:
    print('Signing image.  Enter your passphrase below.')
    gpg_signature = get_gpg_signature(output_filename, keyid=config['keyid'])

if options.certificate:
    print('Generating certificate...', end='')
    make_certificate(svg_filename, gpg_signature, datetime.now().strftime("%Y-%m-%d"))
    print('Done.')


# TODO:
# - Refactor all this into classes
# - Add UI
# - Connect to keepass to store steno passwords
# - Use GPG passphrase from keepass
