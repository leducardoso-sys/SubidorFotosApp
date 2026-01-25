import flet as ft
import requests
import base64
from PIL import Image, ImageOps
import io
import os

# --- CONFIGURACIÓN ---
# 1. TU URL DEL SCRIPT
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx15eHYTxUB-mQ1ZAvDLh7MAJbD9RQi5oaxAfJwgfSeaYeSB8HT3qVmg8usyujsUnouMQ/exec"

# 2. EL ID DE TU CARPETA
DRIVE_FOLDER_ID = "1NMQDc_8bFfl4s_WVSX7pAKBUhckHRu4v"

# Carpeta temporal
TEMP_UPLOAD_DIR = "assets"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

def main(page: ft.Page):
    page.title = "Fotos Cloud"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.padding = 20
    
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    
    # --- LÓGICA DE SUBIDA ---
    def procesar_final(nombre_fichero_servidor):
        try:
            # Filtro de seguridad: Si suben un PDF o algo raro, lo ignoramos o intentamos procesar
            # Como es "ANY", intentamos procesarlo igual. Si falla PIL, es que no era imagen.
            if not nombre_fichero_servidor.lower().endswith(('.png', '.jpg', '.jpeg')):
                 estado_texto.current.value = "⚠️ Error: Debes subir una FOTO, no otro archivo."
                 estado_texto.current.color = "red"
                 estado_texto.current.update()
                 return

            estado_texto.current.value = "☁️ Enviando a la Nube..."
            estado_texto.current.update()

            # Nombre limpio
            raw_name = nombre_archivo.current.value.strip()
            base_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            final_name = f"{base_name}.jpg"

            # Ruta local
            ruta_local = os.path.join(TEMP_UPLOAD_DIR, nombre_fichero_servidor)

            # Optimizar Imagen
            img = Image.open(ruta_local)
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            if img.mode != "RGB": img = img.convert("RGB")
            
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=70, optimize=True)
            img_str = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

            # Enviar a Google Script
            payload = {
                "filename": final_name,
                "file": img_str,
                "mimeType": "image/jpeg"
            }
            
            response = requests.post(APPS_SCRIPT_URL, json=payload)
            
            if response.status_code == 200 and "success" in response.text:
                estado_texto.current.value = f"✅ ¡GUARDADA!\n{final_name}"
                estado_texto.current.color = "green"
                nombre_archivo.current.value = ""
                nombre_archivo.current.update()
            else:
                raise Exception(f"Error Script: {response.text}")

            estado_texto.current.update()
            
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

    def abrir_drive(e):
        drive_url = f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"
        page.launch_url(drive_url)

    # --- VALIDACIÓN Y CAMBIO DE ESTRATEGIA ---
    def validar_y_abrir_camara(e):
        texto = nombre_archivo.current.value
        if not texto or texto.strip() == "":
            nombre_archivo.current.error_text = "⚠️ ¡Pon un nombre primero!"
            nombre_archivo.current.update()
            estado_texto.current.value = "⚠️ Debes escribir el nombre antes."
            estado_texto.current.color = "red"
            estado_texto.current.update()
        else:
            nombre_archivo.current.error_text = None
            nombre_archivo.current.update()
            estado_texto.current.value = "Selecciona CÁMARA..."
            estado_texto.current.color = "blue"
            estado_texto.current.update()
            
            # TRUCO: Usamos ANY (Cualquiera) para forzar al móvil a preguntar "¿Qué quieres usar?"
            file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.ANY)

    file_picker = ft.FilePicker(on_result=iniciar_subida, on_upload=on_upload_progress)
    page.overlay.append(file_picker)

    # --- INTERFAZ ---
    page.add(
        ft.Column([
            ft.Icon(name="cloud_upload", size=60, color="blue"),
            ft.Text("Fotos Cloud", size=30, weight="bold", color="blue"),
            ft.Container(height=20),
            
            ft.TextField(ref=nombre_archivo, label="Nombre (ej: Habitación 500)", border_color="blue", text_align="center"),
            ft.Container(height=10),
            
            ft.ElevatedButton("HACER FOTO", icon="camera_alt", 
                style=ft.ButtonStyle(bgcolor="blue", color="white", padding=20, shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=validar_y_abrir_camara, width=280),
            
            ft.Container(height=10),

            ft.ElevatedButton("VER CARPETA DRIVE", icon="folder_open",
                style=ft.ButtonStyle(bgcolor="green", color="white", padding=20, shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=abrir_drive, width=280),

            ft.Container(height=20),
            ft.Text(ref=estado_texto, value="Listo", size=14, color="grey"),
            
            ft.Container(height=40),
            ft.Text("By Eduardo Cardoso 2026 versión 1.00", size=12, color="grey", weight="bold")
            
        ], alignment="center", horizontal_alignment="center")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0", upload_dir=TEMP_UPLOAD_DIR)

