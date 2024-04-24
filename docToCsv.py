#!/usr/bin/env python

import easyocr
from pdf2image import convert_from_path
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

    convert_from_path(in_file, output_folder=tmp_out, fmt='png')
    return 0


    reader = easyocr.Reader(['en', 'de']) # this needs to run only once to load the model into memory
    result = reader.readtext('')
    return 0

if __name__ == '__main__':
    main()
