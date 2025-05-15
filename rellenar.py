from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName, PdfString
from io import BytesIO
from PyPDF2 import PdfReader as PdfReader_pypdf2, PdfWriter as PdfWriter_pypdf2
from PyPDF2.generic import NameObject, BooleanObject

# ---------- MEDICINA FAMILIAR ----------

from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName, PdfString
from io import BytesIO

def rellenar_formulario_medicina_familiar(estudiante, plantilla_path='static/pdf/plantilla_medicina_familiar.pdf'):
    pdf = PdfReader(plantilla_path)

    if not getattr(pdf, 'Root', None) or not getattr(pdf.Root, 'AcroForm', None):
        pdf.Root.AcroForm = PdfDict()

    pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfName('true')))

    for page in pdf.pages:
        annotations = page['/Annots'] if '/Annots' in page else []
        for annotation in annotations:
            if annotation['/Subtype'] == '/Widget' and annotation.get('/T'):
                key = annotation['/T'][1:-1]
                value = ''
                if key == 'nombre_apellido':
                    value = estudiante.get('nombre_completo', '')
                elif key == 'fecha_nacimiento':
                    value = estudiante.get('fecha_nacimiento', '')
                elif key == 'edad':
                    value = estudiante.get('edad', '')
                elif key == 'nacionalidad':
                    value = estudiante.get('nacionalidad', '')
                elif key == 'rut':
                    value = estudiante.get('rut', '')
                if key == 'genero_f' and estudiante.get('sexo', '').lower() == 'femenino':
                  annotation.update(PdfDict(V=PdfString.encode('X'), Ff=1))
                elif key == 'genero_m' and estudiante.get('sexo', '').lower() == 'masculino':
                  annotation.update(PdfDict(V=PdfString.encode('X'), Ff=1))



                if value != '':
                    annotation.update(PdfDict(V=PdfString.encode(value), Ff=1))

    output = BytesIO()
    PdfWriter().write(output, pdf)
    output.seek(0)
    return output

# ---------- NEUROLOGÍA ----------
def rellenar_formulario_neuro(estudiante, plantilla_path='static/pdf/plantilla_neurologia.pdf'):
    pdf = PdfReader(plantilla_path)

    if not getattr(pdf, 'Root', None) or not getattr(pdf.Root, 'AcroForm', None):
        pdf.Root.AcroForm = PdfDict()

    pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfName('true')))

    for page in pdf.pages:
        annotations = page['/Annots'] if '/Annots' in page else []
        for annotation in annotations:
            if annotation['/Subtype'] == '/Widget' and annotation.get('/T'):
                key = annotation['/T'][1:-1]
                value = ''
                if key == 'nombre_apellido':
                    value = estudiante.get('nombre_completo', '')
                elif key == 'fecha_nacimiento':
                    value = estudiante.get('fecha_nacimiento', '')
                elif key == 'edad':
                    value = estudiante.get('edad', '')
                elif key == 'nacionalidad':
                    value = estudiante.get('nacionalidad', '')
                elif key == 'rut':
                    value = estudiante.get('rut', '')
                elif key == 'genero_f':
                 if key == 'genero_f' and estudiante.get('sexo', '').lower() == 'femenino':
                    annotation.update(PdfDict(V=PdfString.encode('X'), Ff=1))
                elif key == 'genero_m' and estudiante.get('sexo', '').lower() == 'masculino':
                     annotation.update(PdfDict(V=PdfString.encode('X'), Ff=1))



                if value != '':
                    annotation.update(PdfDict(V=PdfString.encode(value), Ff=1))

    output = BytesIO()
    PdfWriter().write(output, pdf)
    output.seek(0)
    return output

# ---------- APLANAR PDF ----------
def aplanar_pdf(input_pdf_stream):
    input_pdf_stream.seek(0)
    reader = PdfReader_pypdf2(input_pdf_stream)
    writer = PdfWriter_pypdf2()

    for page in reader.pages:
        writer.add_page(page)

    if "/AcroForm" in reader.trailer["/Root"]:
        writer._root_object.update({
            NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]
        })
        writer._root_object["/AcroForm"].update({
            NameObject("/NeedAppearances"): BooleanObject(True)
        })

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# ---------- DEBUG CAMPOS PDF ----------
def debug_campos_pdf(plantilla_path):
    pdf = PdfReader(plantilla_path)
    print("Campos de formulario encontrados:\n")

    if not pdf.pages:
        print("⚠️ No hay páginas en el PDF.")
        return

    for page_num, page in enumerate(pdf.pages, start=1):
        annots = page.get('/Annots')
        if annots:
            print(f"📄 Página {page_num}:")
            for annot in annots:
                t = annot.get('/T')
                ft = annot.get('/FT')
                if t:
                    print(f"  • Campo: {t} | Tipo: {ft}")
        else:
            print(f"📄 Página {page_num}: sin campos")

# ---------- INFERIR SEXO ----------
def inferir_sexo(nombre_completo):
    if not nombre_completo:
        return ""

    nombre = str(nombre_completo).strip().split()[0].lower()

    femeninos = ('a', 'na', 'ia', 'ta', 'ela', 'isa')
    masculinos = ('o', 'el', 'an', 'al', 'io')

    if nombre.endswith(femeninos):
        return 'femenino'
    elif nombre.endswith(masculinos):
        return 'masculino'
    else:
        return ''





