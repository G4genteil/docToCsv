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
        res += [reader.readtext(str(img), paragraph=False)]

    return res

def convert_data(pages: list[list[list]]) -> list[list[dict[str]]]:
    res = []
    for page in pages:
        page_conv = []
        for line in page:
            data = {
                'coords': [int(x) for x in line[0][0]],
                'text': line[1],
            }
            page_conv += [data]
            #print(json.dumps(data) + ',')

        res += [page_conv]

    return res

def gen_csv(pages: list[list[dict[str]]]) -> None:
    for page in pages:

        abholaddresse_pos = None
        mat_nr_pos = None
        mat_bez_pos = None
        anz_ret_pos = None
        ret_grund_pos = None
        retouren_nr_pos = None
        anmelde_datum = None
        anmeldeDatumGesehen = False
        ret_nr = None
        retourenNummerGesehen = False
        versandTag = None
        versandTagGesehen = False;
        lieferTour = None;
        lieferTourGesehen = False;
        abholTour = None;
        abholTourGesehen = False;


        for line in page:
            text: str = line['text']
            coords: list[int] = line['coords']

            if 'Abholadresse' in text:
                abholaddresse_pos = coords
            if 'Material-Nr' in text:
                mat_nr_pos = coords
            if 'Material-Bezeichnung' in text:
                mat_bez_pos = coords
            if 'Retourengrund' in text:
                anz_ret_pos = coords
            if 'Ret.' == text:
                ret_grund_pos = coords
            if 'Retouren-Nr.' in text:
                retouren_nr_pos = coords

            # Anmeldedatum
            if 'Anmeldedatum:' == text:
                anmeldeDatumGesehen = True
            elif anmeldeDatumGesehen:
                anmelde_datum = text
                anmeldeDatumGesehen = False
            elif 'Anmeldedatum:' in text:
                anmelde_datum = text.split(': ')[1].strip()

            # Retourennummer
            if 'Retouren-Nr.:' == text:
                retourenNummerGesehen = True
            elif retourenNummerGesehen:
                ret_nr = text
                retourenNummerGesehen = False
            elif 'Retouren-Nr.:' in text:
                ret_nr = text.split(': ')[1].strip()

            # Versandtag
            if 'Lieferschein:' == text:
                versandTagGesehen = True
            elif versandTagGesehen:
                versandTag = text.split('vom ')[1].strip()
                versandTagGesehen = False
            elif 'Lieferschein:' in text:
                versandTag = text.split('vom ')[1].strip()

            # Liefertour
            if 'Auslief.-tour:' == text:
                lieferTourGesehen = True
            elif lieferTourGesehen:
                lieferTour = text
                lieferTourGesehen = False
            elif 'Auslief.-tour:' in text:
                lieferTour = text

            # Abholtour
            if 'Abholtour:' == text:
                abholTourGesehen = True
            elif abholTourGesehen:
                abholTour = text
                abholTourGesehen = False
            elif 'Abholtour:' in text:
                abholTour = text

        print(f'abholaddresse_pos: {abholaddresse_pos}')
        print(f'mat_nr:            {mat_nr_pos}')
        print(f'mat_bez:           {mat_bez_pos}')
        print(f'anz_ret:           {anz_ret_pos}')
        print(f'retouren_nr_pos:   {retouren_nr_pos}')
        print(f'ret_grund:         {ret_grund_pos}')
        print(f'anmelde_datum:     {anmelde_datum}')
        print(f'ret_nr:            {ret_nr}')
        print(f'versandTag:        {versandTag}')
        print(f'liefertour:        {lieferTour}')
        print(f'abholtour:         {abholTour}')




        abholaddresse_spalte = [x for x in page if abs(x['coords'][0] - abholaddresse_pos[0]) < 16]
        abholaddresse_spalte = [x for x in abholaddresse_spalte if x['coords'][1] < retouren_nr_pos[1]]
        abholaddresse_spalte = sorted(abholaddresse_spalte, key=lambda x: x['coords'][1])

        # Kundennummer ist immer direkt unter der UEberschrift
        kundennummer = int(abholaddresse_spalte[1]['text'])
        # Kundenbezeichung ist direkt drunter
        kundenbez = abholaddresse_spalte[2]['text']

        # Postleizahl ist das letzte element
        plz_el = abholaddresse_spalte[-1]
        plz_txt: str = plz_el['text'].strip()
        ort: str = None
        if ' ' in plz_txt:
            ort = plz_txt.split(' ')[-1].strip()
        else:
            ort = page[page.index(plz_el) + 1]['text']

        print(f'kundennummer:      {kundennummer}')
        print(f'kundenbez:         {kundenbez}')
        print(f'ort:               {ort}')

        for i in abholaddresse_spalte:
            print(i)


def main() -> int:
    parser = AP.ArgumentParser('Doc To CSV')
    parser.add_argument('input', type=Path, help='Pfad zur input PDF Datei')

    args = parser.parse_args()

    in_file: Path = args.input

    #extract_images(in_file)
    #pages = read_images()
    #pages = convert_data(pages)
    pages = json.loads((ROOT / 'data.json').read_text())
    gen_csv(pages)


if __name__ == '__main__':
    raise SystemExit(main())
