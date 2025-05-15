from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import openpyxl
import os
import time
import datetime
import zipfile
from io import BytesIO
from pdfrw import PdfReader as PdfReader_pdfrw, PdfWriter as PdfWriter_pdfrw, PdfDict, PdfName
from PyPDF2 import PdfReader as PdfReader_pypdf2, PdfWriter as PdfWriter_pypdf2
from PyPDF2.generic import NameObject, BooleanObject
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, TextStringObject, DictionaryObject, BooleanObject
from io import BytesIO
from rellenar import rellenar_formulario_medicina_familiar, rellenar_formulario_neuro, aplanar_pdf



# --- Configuración inicial ---
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Usuarios ---
usuarios = {
    "admin@cardiohome.cl": {"password": "admin123", "tipo": "admin"},
    "medico@cardiohome.cl": {"password": "medico123", "tipo": "medico"}
}

# --- Funciones auxiliares ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def inferir_sexo(nombre_completo):
    nombre = nombre_completo.lower()
    if any(word in nombre for word in ['juan', 'pedro', 'felipe', 'carlos', 'diego', 'matías']):
        return 'Masculino'
    elif any(word in nombre for word in ['maría', 'camila', 'fernanda', 'sofia', 'josefa', 'valentina']):
        return 'Femenino'
    else:
        return 'No definido'

import datetime
import openpyxl

def procesar_planilla(filepath):
    wb = openpyxl.load_workbook(filepath)
    sheet = wb.active

    headers = [str(cell.value).strip().lower() if cell.value else None for cell in sheet[1]]
    estudiantes = []

    for fila_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if all(cell is None for cell in row):
            continue

        estudiante = {}
        try:
            for idx, value in enumerate(row):
                if idx >= len(headers):
                    continue
                header = headers[idx]
                if not header:
                    continue

                if 'nombre' in header and isinstance(value, str):
                    estudiante['nombre_completo'] = value.strip()
                elif 'rut' in header:
                    estudiante['rut'] = str(value).strip() if value else ''
                elif 'fecha' in header or 'nacimiento' in header:
                    if isinstance(value, datetime.date):
                        estudiante['fecha_nacimiento'] = value.strftime("%d-%m-%Y")
                    elif isinstance(value, str):
                        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                            try:
                                fecha = datetime.datetime.strptime(value.strip(), fmt)
                                estudiante['fecha_nacimiento'] = fecha.strftime("%d-%m-%Y")
                                break
                            except ValueError:
                                continue
                        else:
                            estudiante['fecha_nacimiento'] = None
                    else:
                        estudiante['fecha_nacimiento'] = None
                elif 'nacionalidad' in header and isinstance(value, str):
                    estudiante['nacionalidad'] = value.strip()

            # Validación clave
            if estudiante.get('nombre_completo') and estudiante.get('rut'):
                estudiante['sexo'] = inferir_sexo(estudiante['nombre_completo'])
                estudiantes.append(estudiante)
            else:
                print(f"⚠️ Fila {fila_num} omitida: faltan nombre o rut.")

        except Exception as e:
            print(f"❌ Error en fila {fila_num}: {e}")
            continue

    print(f"✅ Total estudiantes cargados: {len(estudiantes)}")
    return estudiantes



def calcular_edad_texto(fecha_nacimiento):
    if not fecha_nacimiento:
        return ""
    nacimiento = datetime.datetime.strptime(fecha_nacimiento, "%d-%m-%Y")
    hoy = datetime.datetime.today()
    años = hoy.year - nacimiento.year
    meses = hoy.month - nacimiento.month
    if hoy.day < nacimiento.day:
        meses -= 1
    if meses < 0:
        años -= 1
        meses += 12
    return f"{años} años {meses} meses"

from pdfrw import PdfReader as PdfReader_pdfrw, PdfWriter as PdfWriter_pdfrw, PdfDict, PdfName, PdfString
from PyPDF2 import PdfReader as PdfReader_pypdf2, PdfWriter as PdfWriter_pypdf2
from io import BytesIO

def rellenar_formulario_medicina_familiar(estudiante, plantilla_path='static/pdf/plantilla_medicina_familiar.pdf'):
    plantilla = PdfReader_pdfrw(plantilla_path)
    if not plantilla.Root.AcroForm:
        plantilla.Root.AcroForm = PdfDict()
    plantilla.Root.AcroForm.update(PdfDict(NeedAppearances=PdfName('true')))

    for page in plantilla.pages:
        annotations = page['/Annots']
        if annotations:
            for annotation in annotations:
                if annotation['/Subtype'] == '/Widget' and annotation['/T']:
                    key = annotation['/T'][1:-1]
                    if key == 'nombre_apellido':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante['nombre_completo']), Ff=1))
                    elif key == 'fecha_nacimiento':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante['fecha_nacimiento']), Ff=1))
                    elif key == 'edad':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante.get('edad', '')), Ff=1))
                    elif key == 'nacionalidad':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante['nacionalidad']), Ff=1))
                    elif key == 'rut':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante.get('rut', '')), Ff=1))
                    elif key == 'genero_f' and estudiante['sexo'].lower() == 'femenino':
                        annotation.update(PdfDict(AS=PdfName('Yes')))
                    elif key == 'genero_m' and estudiante['sexo'].lower() == 'masculino':
                        annotation.update(PdfDict(AS=PdfName('Yes')))

    output_stream = BytesIO()
    PdfWriter_pdfrw().write(output_stream, plantilla)
    output_stream.seek(0)
    return output_stream

def rellenar_formulario_neuro(estudiante, plantilla_path='static/pdf/plantilla_neurologia.pdf'):
    plantilla = PdfReader_pdfrw(plantilla_path)
    if not plantilla.Root.AcroForm:
        plantilla.Root.AcroForm = PdfDict()
    plantilla.Root.AcroForm.update(PdfDict(NeedAppearances=PdfName('true')))

    for page in plantilla.pages:
        annotations = page['/Annots']
        if annotations:
            for annotation in annotations:
                if annotation['/Subtype'] == '/Widget' and annotation['/T']:
                    key = annotation['/T'][1:-1]
                    if key == 'nombre_apellido':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante['nombre_completo']), Ff=1))
                    elif key == 'fecha_nacimiento':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante['fecha_nacimiento']), Ff=1))
                    elif key == 'edad':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante.get('edad', '')), Ff=1))
                    elif key == 'nacionalidad':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante['nacionalidad']), Ff=1))
                    elif key == 'rut':
                        annotation.update(PdfDict(V=PdfString.encode(estudiante.get('rut', '')), Ff=1))
                    elif key == 'genero_F' and estudiante['sexo'].lower() == 'femenino':
                        annotation.update(PdfDict(AS=PdfName('Yes')))
                    elif key == 'genero_M' and estudiante['sexo'].lower() == 'masculino':
                        annotation.update(PdfDict(AS=PdfName('Yes')))

    output_stream = BytesIO()
    PdfWriter_pdfrw().write(output_stream, plantilla)
    output_stream.seek(0)
    return output_stream

def aplanar_pdf(input_pdf_stream):
    input_pdf_stream.seek(0)
    reader = PdfReader_pypdf2(input_pdf_stream)
    writer = PdfWriter_pypdf2()

    for page in reader.pages:
        writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream


from pdfjinja import PdfJinja
from io import BytesIO

def rellenar_formulario_pdfjinja(estudiante, plantilla_path):
    pdf_template = PdfJinja(plantilla_path)
    
    data = {
        "nombre_apellido": estudiante.get("nombre_completo", ""),
        "fecha_nacimiento": estudiante.get("fecha_nacimiento", ""),
        "edad": estudiante.get("edad", ""),
        "nacionalidad": estudiante.get("nacionalidad", ""),
        "rut": estudiante.get("rut", ""),
        "genero_F": "Yes" if estudiante.get("sexo", "").lower() == "femenino" else None,
        "genero_M": "Yes" if estudiante.get("sexo", "").lower() == "masculino" else None
    }

    output = BytesIO()
    pdf_template(data).write(output)
    output.seek(0)
    return output


def rellenar_formulario_pypdf_forzado(estudiante, plantilla_path):
    reader = PdfReader(plantilla_path)
    PdfWriter().write(output_stream, trailer=plantilla)


    page = reader.pages[0]
    writer.add_page(page)

    campos = {
        "nombre_apellido": estudiante.get("nombre_completo", ""),
        "fecha_nacimiento": estudiante.get("fecha_nacimiento", ""),
        "edad": estudiante.get("edad", ""),
        "nacionalidad": estudiante.get("nacionalidad", ""),
        "rut": estudiante.get("rut", ""),
    }

    # Sexo
    if estudiante.get("sexo", "").lower() == "femenino":
        campos["genero_F"] = "/Yes"
    elif estudiante.get("sexo", "").lower() == "masculino":
        campos["genero_M"] = "/Yes"

    # Rellenamos los campos
    writer.update_page_form_field_values(writer.pages[0], campos)

    # 🛠️ OBLIGAMOS a que las apariencias se actualicen
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update({
            NameObject("/NeedAppearances"): BooleanObject(True)
        })

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output


# --- Las rutas (@app.route) ---
# (TE MANDO A CONTINUACIÓN SI QUIERES TODO EL BLOQUE DE RUTAS ORDENADO)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = usuarios.get(email)
        if user and user['password'] == password:
            session['usuario'] = email
            session['tipo'] = user['tipo']
            if user['tipo'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['tipo'] == 'medico':
                return redirect(url_for('admin_dashboard'))  # Puedes cambiar a otra vista si quieres
        else:
            flash('Correo o contraseña incorrectos', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/proyectos', methods=['GET', 'POST'])
def admin_proyectos():
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        nombre_proyecto = request.form['nombre_proyecto']
        if 'proyectos' not in session:
            session['proyectos'] = {}
        if nombre_proyecto not in session['proyectos']:
            session['proyectos'][nombre_proyecto] = {}
        session.modified = True
        flash(f"Proyecto {nombre_proyecto} creado exitosamente", 'success')
        return redirect(url_for('admin_proyectos'))
    proyectos = list(session.get('proyectos', {}).keys())
    return render_template('admin_proyectos.html', proyectos=proyectos)

@app.route('/admin/proyectos/<nombre_proyecto>/agregar_colegio', methods=['GET', 'POST'])
def agregar_colegio(nombre_proyecto):
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        nombre_colegio = request.form['nombre_colegio']
        if 'proyectos' in session and nombre_proyecto in session['proyectos']:
            session['proyectos'][nombre_proyecto][nombre_colegio] = []
            session.modified = True
            flash(f"Colegio {nombre_colegio} agregado exitosamente", 'success')
            return redirect(url_for('ver_proyecto', nombre_proyecto=nombre_proyecto))
    return render_template('agregar_colegio.html', nombre_proyecto=nombre_proyecto)

@app.route('/admin/proyectos/<nombre_proyecto>')
def ver_proyecto(nombre_proyecto):
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    colegios = list(session.get('proyectos', {}).get(nombre_proyecto, {}).keys())
    return render_template('ver_proyecto.html', nombre_proyecto=nombre_proyecto, colegios=colegios)


@app.route('/admin')
def inicio():
    return render_template('inicio.html')

@app.route('/admin/proyectos/<nombre_proyecto>/<nombre_colegio>')
def ver_colegio(nombre_proyecto, nombre_colegio):
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    proyectos = session.get('proyectos', {})
    estudiantes = []
    formularios_medicina = []
    formularios_neurologia = []
    if nombre_proyecto in proyectos and nombre_colegio in proyectos[nombre_proyecto]:
        estudiantes = proyectos[nombre_proyecto][nombre_colegio]
        base_path = os.path.join(app.config['UPLOAD_FOLDER'], nombre_proyecto, nombre_colegio)
        medicina_path = os.path.join(base_path, 'Formularios Medicina Familiar')
        neurologia_path = os.path.join(base_path, 'Formularios Neurologia')
        if os.path.exists(medicina_path):
            formularios_medicina = [{'nombre': f, 'fecha': time.ctime(os.path.getctime(os.path.join(medicina_path, f))), 'estado': 'Listo'} for f in os.listdir(medicina_path) if f.endswith('.pdf')]
        if os.path.exists(neurologia_path):
            formularios_neurologia = [{'nombre': f, 'fecha': time.ctime(os.path.getctime(os.path.join(neurologia_path, f))), 'estado': 'Listo'} for f in os.listdir(neurologia_path) if f.endswith('.pdf')]
    return render_template('ver_colegio.html', nombre_proyecto=nombre_proyecto, nombre_colegio=nombre_colegio, estudiantes=estudiantes, formularios_medicina=formularios_medicina, formularios_neurologia=formularios_neurologia)

@app.route('/admin/planillas')
def admin_planillas():
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_planillas.html')

from rellenar import rellenar_formulario_medicina_familiar, rellenar_formulario_neuro, aplanar_pdf

@app.route('/admin/proyectos/<nombre_proyecto>/<nombre_colegio>/subir', methods=['GET', 'POST'])
def subir_excel_formulario(nombre_proyecto, nombre_colegio):
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No seleccionaste archivo', 'error')
            return redirect(request.url)

        file = request.files['file']
        tipo_formulario = request.form.get('tipo_formulario')

        if file.filename == '' or not allowed_file(file.filename):
            flash('Archivo inválido', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        estudiantes = procesar_planilla(filepath)
        estudiantes.sort(key=lambda x: x['nombre_completo'])

        if len(estudiantes) == 0:
            flash("No se han encontrado estudiantes en el archivo", "error")
            return redirect(request.url)

        carpeta_destino = os.path.join(
            app.config['UPLOAD_FOLDER'],
            nombre_proyecto,
            nombre_colegio,
            f"Formularios {tipo_formulario.replace('_', ' ').title()}"
        )
        os.makedirs(carpeta_destino, exist_ok=True)

        for estudiante in estudiantes:
            if estudiante.get('fecha_nacimiento'):
                estudiante['edad'] = calcular_edad_texto(estudiante['fecha_nacimiento'])
            else:
                estudiante['edad'] = ""

            # Generar PDF por cada estudiante
            if tipo_formulario == "medicina_familiar":
                pdf_llenado = rellenar_formulario_medicina_familiar(estudiante)
            elif tipo_formulario == "neurologia":
                pdf_llenado = rellenar_formulario_neuro(estudiante)
            else:
                flash('Tipo de formulario desconocido', 'error')
                return redirect(request.url)

            pdf_final = aplanar_pdf(pdf_llenado)

            nombre_archivo = f"{estudiante['nombre_completo'].replace(' ', '_')}_formulario_{tipo_formulario}.pdf"
            ruta_final = os.path.join(carpeta_destino, nombre_archivo)

            with open(ruta_final, 'wb') as f:
                f.write(pdf_final.read())

        flash(f"Se generaron {len(estudiantes)} formularios en {tipo_formulario.replace('_', ' ').title()}", "success")
        return redirect(url_for('ver_colegio', nombre_proyecto=nombre_proyecto, nombre_colegio=nombre_colegio))

    return render_template('subir_excel_formulario.html', nombre_proyecto=nombre_proyecto, nombre_colegio=nombre_colegio)


@app.route('/admin/proyectos/<nombre_proyecto>/<nombre_colegio>/descargar/<tipo_formulario>/<filename>')
def descargar_pdf_individual(nombre_proyecto, nombre_colegio, tipo_formulario, filename):
    carpeta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_proyecto, nombre_colegio, f'Formularios {tipo_formulario.replace("_", " ").title()}')
    ruta_pdf = os.path.join(carpeta, filename)
    if not os.path.exists(ruta_pdf):
        flash('El formulario no existe', 'error')
        return redirect(url_for('ver_colegio', nombre_proyecto=nombre_proyecto, nombre_colegio=nombre_colegio))
    return send_file(ruta_pdf, as_attachment=True)

@app.route('/admin/proyectos/<nombre_proyecto>')
def ver_proyecto_unico(nombre_proyecto):
    # Aquí deberías cargar los colegios de ese proyecto
    return render_template('ver_proyecto.html', nombre_proyecto=nombre_proyecto)

@app.route('/derivaciones')
def derivaciones():
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    return render_template('derivaciones.html')

@app.route('/admin/proyectos/<nombre_proyecto>/<nombre_colegio>/descargar/<tipo_formulario>')
def descargar_formularios(nombre_proyecto, nombre_colegio, tipo_formulario):
    carpeta_base = os.path.join(app.config['UPLOAD_FOLDER'], nombre_proyecto, nombre_colegio, f'Formularios {tipo_formulario.replace("_", " ").title()}')
    if not os.path.exists(carpeta_base):
        flash('No se encontraron formularios de este tipo', 'error')
        return redirect(url_for('ver_colegio', nombre_proyecto=nombre_proyecto, nombre_colegio=nombre_colegio))
    memoria_zip = BytesIO()
    with zipfile.ZipFile(memoria_zip, 'w') as zf:
        for filename in os.listdir(carpeta_base):
            ruta_archivo = os.path.join(carpeta_base, filename)
            if os.path.isfile(ruta_archivo):
                zf.write(ruta_archivo, arcname=filename)
    memoria_zip.seek(0)
    nombre_zip = f"{nombre_colegio.replace(' ', '_')}_{tipo_formulario}.zip"
    return send_file(memoria_zip, mimetype='application/zip', as_attachment=True, download_name=nombre_zip)

@app.route('/firmar_pdf', methods=['GET', 'POST'])
@login_required
def firmar_pdf():
    if request.method == 'POST':
        files = request.files.getlist('pdfs')
        signed_pdfs = []
        for file in files:
            if file.filename.endswith('.pdf'):
                pdf_bytes = file.read()
                signed_pdf = firmar_pdf_con_firma(pdf_bytes)
                signed_pdfs.append((f"signed_{file.filename}", signed_pdf))

        if len(signed_pdfs) == 1:
            filename, filedata = signed_pdfs[0]
            return send_file(filedata, as_attachment=True, download_name=filename, mimetype='application/pdf')

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for filename, filedata in signed_pdfs:
                zipf.writestr(filename, filedata.getvalue())
        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name="documentos_firmados.zip", mimetype='application/zip')

    return render_template('firmar_pdf.html')

from flask import send_file, render_template, request
import fitz
from io import BytesIO
import zipfile
import os
from flask_login import login_required


def firmar_pdf_con_firma(pdf_data):
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    signature = fitz.Pixmap("static/signature.png")
    sig_width = 110
    sig_height = 50
    for page in doc:
        x0 = 370
        y0 = 750
        sig_rect = fitz.Rect(x0, y0, x0 + sig_width, y0 + sig_height)
        page.insert_image(sig_rect, pixmap=signature, overlay=True)
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output



if __name__ == '__main__':
    app.run(debug=True)

















