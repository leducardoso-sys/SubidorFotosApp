import flet as ft
import requests
import base64
from PIL import Image, ImageOps
import io
import datetime
import os

# --- CONFIGURACIÓN ---
# ¡PEGA AQUÍ LA URL QUE TE DIO GOOGLE APPS SCRIPT!
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzp9ONQgK-qj5M0d13PKIKyRNpq664yyv5pHI3hDI_VcUSisWLRsUxCW2j8_wMSVYCkPw/exec"

# Carpeta temporal
TEMP_UPLOAD_DIR = "assets"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

def main(page: ft.Page):
    page.title = "Senator Cloud"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.padding = 20
    
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    
    def procesar_final(nombre_fichero_servidor):
        try:
            estado_texto.current.value = "☁️ Enviando a la Nube..."
            estado_texto.current.update()

            # 1. Preparar nombre
            raw_name = nombre_archivo.current.value.strip()
            if not raw_name: raw_name = "foto"
            base_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{base_name}_{timestamp}.jpg"

            # 2. Ruta local
            ruta_local = os.path.join(TEMP_UPLOAD_DIR, nombre_fichero_servidor)

            # 3. Optimizar Imagen
            img = Image.open(ruta_local)
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            if img.mode != "RGB": img = img.convert("RGB")
            
            # Convertir a Base64 para enviar por el "Túnel"
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=70, optimize=True)
            img_str = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

            # 4. ENVIAR A GOOGLE SCRIPT
            payload = {
                "filename": final_name,
                "file": img_str,
                "mimeType": "image/jpeg"
            }
            
            response = requests.post(APPS_SCRIPT_URL, json=payload)
            
            if response.status_code == 200 and "success" in response.text:
                estado_texto.current.value = f"✅ ¡GUARDADA EN DRIVE!\n{final_name}"
                estado_texto.current.color = "green"
            else:
                raise Exception(f"Error Script: {response.text}")

            estado_texto.current.update()
            nombre_archivo.current.value = ""
            nombre_archivo.current.update()
            
            # Limpieza
            if os.path.exists(ruta_local):
                os.remove(ruta_local)

        except Exception as ex:
            estado_texto.current.value = f"❌ Error: {str(ex)}"
            estado_texto.current.color = "red"
            estado_texto.current.update()
            print(ex)

    def on_upload_progress(e: ft.FilePickerUploadEvent):
        if e.error:
            estado_texto.current.value = f"Error subida: {e.error}"
            estado_texto.current.color = "red"
            estado_texto.current.update()
            return  
        if e.progress == 1.0:
            procesar_final(e.file_name)

    def iniciar_subida(e: ft.FilePickerResultEvent):
        if not e.files: return
        estado_texto.current.value = "⬆️ Subiendo..."
        estado_texto.current.color = "orange"
        estado_texto.current.update()
        
        files_to_upload = []
        for f in e.files:
            upload_url = page.get_upload_url(f.name, 600)
            files_to_upload.append(ft.FilePickerUploadFile(f.name, upload_url=upload_url))
        file_picker.upload(files_to_upload)

    file_picker = ft.FilePicker(on_result=iniciar_subida, on_upload=on_upload_progress)
    page.overlay.append(file_picker)

    page.add(
        ft.Column([
            ft.Icon(name="cloud_upload", size=60, color="blue"),
            ft.Text("Subir a Carpeta", size=24, weight="bold"),
            ft.Container(height=20),
            ft.TextField(ref=nombre_archivo, label="Nombre (ej: Habitación 500)", border_color="blue", text_align="center"),
            ft.Container(height=10),
            ft.ElevatedButton("HACER FOTO", icon="camera_alt", 
                style=ft.ButtonStyle(bgcolor="blue", color="white", padding=20, shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=lambda _: file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE), width=280),
            ft.Container(height=20),
            ft.Text(ref=estado_texto, value="Listo", size=14, color="grey"),
            ft.Container(height=20),
            ft.Text("v13.0 Script Bypass", size=10, color="grey")
        ], alignment="center", horizontal_alignment="center")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # IMPORTANTE: upload_dir="assets" y SIN secret_key aquí
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0", upload_dir=TEMP_UPLOAD_DIR)
