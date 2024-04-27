#!/usr/bin/env python

# from pdf2image import convert_from_path
import fitz
from pathlib import Path
import argparse as AP
import shutil
from PIL import Image
import json
import io

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

            tmp_img = Image.open(io.BytesIO(img_data['image']))
            tmp_img = tmp_img.convert('L')
            tmp_img = tmp_img.rotate(-90, expand=True)
            tmp_img.save(TMP_OUT / f'{img[0]}.png')

def read_images() -> list[list[dict]]:
    import easyocr
    reader = easyocr.Reader(['de']) # this needs to run only once to load the model into memory

    res = []
    for img in TMP_OUT.glob("*"):
        res += [reader.readtext(str(img), paragraph=False, canvas_size=3200)]

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
                ret_grund_pos = coords
            if 'Ret.' == text:
                anz_ret_pos = coords
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

        # Parse Tabelle
        tabelle = [x for x in page if x['coords'][1] > (mat_nr_pos[1] + 16)]
        tabelle_zeilen: list[list[dict[str]]] = []

        curr_y = tabelle[0]['coords'][1]
        curr_zeile = []
        for i in tabelle:
            if abs(curr_y - i['coords'][1]) < 16:
                curr_zeile += [i]
            else:
                tabelle_zeilen += [curr_zeile]
                curr_zeile = [i]
                curr_y = i['coords'][1]

        if curr_zeile:
            tabelle_zeilen += [curr_zeile]

        # Tabelle verwenden
        for line in tabelle_zeilen:
            matnummer = None
            retourengrund = None
            mat_bez = None
            anz_ret = None

            mat_bez_best = 999999
            anz_ret_best = 999999

            for entry in list(line):
                text: str = entry['text']
                coords: list[int] = entry['coords']

                if abs(coords[0] - mat_nr_pos[0]) < 16:
                    matnummer = text
                    line.remove(entry)
                if abs(coords[0] - ret_grund_pos[0]) < 16:
                    retourengrund = text
                    line.remove(entry)

            for entry in line:
                text: str = entry['text']
                coords: list[int] = entry['coords']

                dist_mat_bez = abs(coords[0] - mat_bez_pos[0])
                dist_anz_ret = abs(coords[0] - anz_ret_pos[0])
                if dist_mat_bez < mat_bez_best:
                    mat_bez = text
                    mat_bez_best = dist_mat_bez
                if dist_anz_ret < anz_ret_best:
                    anz_ret = text
                    anz_ret_best = dist_anz_ret

            print(f' - matnummer:      {matnummer}')
            print(f' - retourengrund:  {retourengrund}')
            print(f' - mat. bez.:      {mat_bez} -- [{mat_bez_best}]')
            print(f' - anzahl ret.:    {anz_ret} -- [{anz_ret_best}]')


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
