import fitz  # PyMuPDF

def convertir_pdf_a_imagen(pdf_path, imagen_salida):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    pix.save(imagen_salida)
    doc.close()

if __name__ == "__main__":
    convertir_pdf_a_imagen('FORMATO FAMILIAR CON X CON FIRMA ADRIANA.pdf', 'static/img/fondo_formulario.png')
