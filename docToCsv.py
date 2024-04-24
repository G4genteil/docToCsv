#!/usr/bin/env python

import easyocr
# from pdf2image import convert_from_path
import fitz
from pathlib import Path
import argparse as AP
import shutil

ROOT = Path(__file__).parent.resolve()

def main() -> int:

    parser = AP.ArgumentParser('Doc To CSV')
    parser.add_argument('input', type=Path, help='Pfad zur input PDF Datei')

    args = parser.parse_args()

    in_file: Path = args.input

    tmp_out = ROOT / 'tmp'
    if tmp_out.exists():
        shutil.rmtree(tmp_out)

    tmp_out.mkdir(parents=True)

    pdf = fitz.open(in_file)
    for page in pdf:
        for img in page.get_images():
            img_data = pdf.extract_image(img[0])

            img_out = tmp_out / f'{img[0]}.{img_data["ext"]}'
            img_out.write_bytes(img_data['image'])

    reader = easyocr.Reader(['en', 'de']) # this needs to run only once to load the model into memory

    for img in tmp_out.glob("*"):
        print(img)
        result = reader.readtext(img)
        print(result)


    return 0

    return 0

if __name__ == '__main__':
    main()
