#!/usr/bin/env python

# from pdf2image import convert_from_path
import fitz
from pathlib import Path
import argparse as AP
import shutil
from PIL import Image
import json
import io
import xlsxwriter
import re
from gooey import Gooey, GooeyParser

ROOT = Path(__file__).parent.resolve()
TMP_OUT = ROOT / 'tmp'

global_file_counter = 0

from pprint import pprint

def extract_images(in_file: Path, rotate: int) -> None:
    print(f'Extrahiere Bilder aus PDF: {in_file}')
    global global_file_counter

    pdf = fitz.open(in_file)
    for page in pdf:
        for img in page.get_images():
            img_data = pdf.extract_image(img[0])

            tmp_img = Image.open(io.BytesIO(img_data['image']))
            tmp_img = tmp_img.convert('L')
            tmp_img = tmp_img.rotate(rotate, expand=True)
            tmp_img.save(TMP_OUT / f'{global_file_counter}.png')
            global_file_counter += 1

def read_images() -> list[list[dict]]:
    print('Lade easyocr...')

    import easyocr
    reader = easyocr.Reader(['de']) # this needs to run only once to load the model into memory

    print('Erkenne texte in den Bildern...')

    res = []
    image_files = list(TMP_OUT.glob("*"))
    for idx, img in enumerate(image_files):
        print(f'progress: {idx}/{len(image_files)}')
        res += [reader.readtext(str(img), paragraph=False, canvas_size=3200)]

    print(f'progress: {len(image_files)}/{len(image_files)}')

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

        res += [page_conv]

    return res

def gen_csv(pages: list[list[dict[str]]], worksheet, max_pix_diff: int) -> None:
    curr_row = 1
    for idx, page in enumerate(pages):
        print(f'\n\n\n\n\nBearbeite Bildaten von Bild {idx}.png')

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

        page = [{'coords': x['coords'], 'text': re.sub(r'\s+\.', '.', x['text'])} for x in page]
        page = [{'coords': x['coords'], 'text': re.sub(r'\s+:', ':', x['text'])} for x in page]

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

        abholaddresse_spalte = [x for x in page if abs(x['coords'][0] - abholaddresse_pos[0]) < max_pix_diff]
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
        tabelle = [x for x in page if x['coords'][1] > (mat_nr_pos[1] + max_pix_diff)]
        tabelle_zeilen: list[list[dict[str]]] = []

        curr_y = tabelle[0]['coords'][1]
        curr_zeile = []
        for i in tabelle:
            if abs(curr_y - i['coords'][1]) < max_pix_diff:
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

                if abs(coords[0] - mat_nr_pos[0]) < max_pix_diff:
                    matnummer = text
                    line.remove(entry)
                if abs(coords[0] - ret_grund_pos[0]) < max_pix_diff:
                    retourengrund = text
                    line.remove(entry)

            for entry in line:
                text: str = entry['text']
                coords: list[int] = entry['coords']

                dist_mat_bez = abs(coords[0] - mat_bez_pos[0])
                dist_anz_ret = abs(coords[0] - anz_ret_pos[0])
                if dist_mat_bez < 200 and dist_mat_bez < mat_bez_best:
                    mat_bez = text
                    mat_bez_best = dist_mat_bez
                if dist_anz_ret < 200 and dist_anz_ret < anz_ret_best:
                    anz_ret = text
                    anz_ret_best = dist_anz_ret

            print(f' - matnummer:      {matnummer}')
            print(f' - retourengrund:  {retourengrund}')
            print(f' - mat. bez.:      {mat_bez} -- [{mat_bez_best}]')
            print(f' - anzahl ret.:    {anz_ret} -- [{anz_ret_best}]')

            # writer.writerow([ret_nr, anmelde_datum, versandTag, mat_bez, anz_ret, retourengrund, kundennummer, kundenbez, ort, lieferTour, abholTour])
            worksheet.write_row(curr_row, 0, [ret_nr, anmelde_datum, versandTag, mat_bez, anz_ret, retourengrund, kundennummer, kundenbez, ort, lieferTour, abholTour])
            curr_row += 1

@Gooey(
    language="german",
    progress_regex=r"^progress: (?P<current>\d+)/(?P<total>\d+)$",
    progress_expr="current / total * 100",
    menu=[
        {
            'name': 'Information', 'items': [
                {
                    'type': 'AboutDialog',
                    'menuTitle': 'Information',
                    'name': 'PDF2Excel',
                    'description': 'Eine einfache Methode für die Retourenlisten',
                    'version': '1.0',
                    'copyright': '2024',
                    'website': 'https://github.com/G4genteil/docToCsv',
                    'developer': 'Leon Schenzel + Daniel Mensinger',
                    'license': 'MIT',
                }
            ]
        }
    ]
)
def main() -> int:
    parser = GooeyParser(description="PDF2Excel")
    parser.add_argument('output', type=Path, help='Pfad zur Ausgabe CSV Datei', widget="FileSaver")
    parser.add_argument('input', type=Path, nargs="+", help='Pfad zur input PDF Datei', widget="MultiFileChooser")
    parser.add_argument('--rotate', '-r', type=float, default=-90, help='Winkel um den die Bilder rotiert werden sollen')
    parser.add_argument('--only-extract', action='store_true', help='Nur die Bilder extrahieren, aber keine Tabelle generieren')

    args = parser.parse_args()

    in_file_list: list[Path] = args.input
    out_file: Path = args.output
    rotate: int = args.rotate
    only_extract: bool = args.only_extract
    max_pix_diff: int = 32

    if not out_file.name.endswith('.xlsx'):
        out_file = out_file.with_suffix('.xlsx')

    if TMP_OUT.exists():
        shutil.rmtree(TMP_OUT)

    TMP_OUT.mkdir(parents=True)

    for file in in_file_list:
        extract_images(file, rotate)

    if only_extract:
        print('Beende mich fruehzeitig!')
        return 0

    pages = read_images()
    pages = convert_data(pages)
    (ROOT / 'data.json').write_text(json.dumps(pages, indent=2))
    #pages = json.loads((ROOT / 'data.json').read_text())

    workbook = xlsxwriter.Workbook(str(out_file))
    worksheet = workbook.add_worksheet()

    cell_format = workbook.add_format()
    cell_format.set_border(1)

    worksheet.set_column(0, 10, 20, cell_format=cell_format)
    worksheet.write_row(0, 0, ["Retouren Nr.", "Anmeldung Datum", "Versandtag", "Kurzbezeichnung", "Anzahl Retouren", "Retourengrund", "Kunde Nr.", "Name", "Ort", "Liefertour", "Abholtour"])
    gen_csv(pages, worksheet, max_pix_diff)
    workbook.close()


if __name__ == '__main__':
    raise SystemExit(main())
