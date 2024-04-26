#!/usr/bin/env python

# from pdf2image import convert_from_path
import fitz
from pathlib import Path
import argparse as AP
import shutil
from PIL import Image
import json

from pprint import pprint

ROOT = Path(__file__).parent.resolve()
TMP_OUT = ROOT / 'tmp'

def extract_images(in_file: Path) -> None:
    if TMP_OUT.exists():
        shutil.rmtree(TMP_OUT)

    TMP_OUT.mkdir(parents=True)

    pdf = fitz.open(in_file)
    for page in pdf:
        for img in page.get_images():
            img_data = pdf.extract_image(img[0])

            img_out = TMP_OUT / f'{img[0]}.{img_data["ext"]}'
            img_out.write_bytes(img_data['image'])

            tmp_img = Image.open(img_out)
            tmp_img = tmp_img.rotate(-90, expand=True)
            tmp_img.save(img_out)

def read_images() -> list[list[dict]]:
    import easyocr
    reader = easyocr.Reader(['de', 'en']) # this needs to run only once to load the model into memory

    res = []
    for img in TMP_OUT.glob("*"):
        res += [reader.readtext(str(img), paragraph=False, output_format='dict')]

    return res

def gen_csv(pages: list[list]) -> None:
    for page in pages:
        for line in page:
            print(json.dumps(line) + ',')
    # pprint(pages)

def main() -> int:
    parser = AP.ArgumentParser('Doc To CSV')
    parser.add_argument('input', type=Path, help='Pfad zur input PDF Datei')

    args = parser.parse_args()

    in_file: Path = args.input

    #extract_images(in_file)
    #pages = read_images()
    pages = json.loads((ROOT / 'data.json').read_text())
    gen_csv(pages)


if __name__ == '__main__':
    raise SystemExit(main())
