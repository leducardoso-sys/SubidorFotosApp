import flet as ft
import requests
import base64
from PIL import Image, ImageOps
import io
import os

# --- CONFIGURACIÓN ---
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx15eHYTxUB-mQ1ZAvDLh7MAJbD9RQi5oaxAfJwgfSeaYeSB8HT3qVmg8usyujsUnouMQ/exec"
DRIVE_FOLDER_ID = "1NMQDc_8bFfl4s_WVSX7pAKBUhckHRu4v"
TEMP_UPLOAD_DIR = "assets"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

def main(page: ft.Page):
    page.title = "Fotos Cloud"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.padding = 20
    
    # Referencias
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    boton_foto = ft.Ref[ft.ElevatedButton]()
    progreso = ft.Ref[ft.ProgressRing]()

    def actualizar_interfaz(texto, color="grey", ocupado=False):
        estado_texto.current.value = texto
        estado_texto.current.color = color
        progreso.current.visible = ocupado
        boton_foto.current.disabled = ocupado
        page.update()

    # --- LÓGICA DE SUBIDA ---
    def procesar_final(nombre_fichero_servidor):
        try:
            if not nombre_fichero_servidor.lower().endswith(('.png', '.jpg', '.jpeg')):
                 actualizar_interfaz("⚠️ Error: Debes subir una FOTO.", "red")
                 return

            actualizar_interfaz("☁️ Enviando a la Nube...", "blue", True)

            # Nombre limpio y seguro
            raw_name = nombre_archivo.current.value.strip()
            base_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            if not base_name: base_name = "foto_sin_nombre"
            final_name = f"{base_name}.jpg"

            ruta_local = os.path.join(TEMP_UPLOAD_DIR, nombre_fichero_servidor)

            # Optimizar Imagen (Uso de 'with' para liberar memoria RAM)
            with Image.open(ruta_local) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                if img.mode != "RGB": img = img.convert("RGB")
                
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="JPEG", quality=65, optimize=True)
                img_str = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

            # Enviar a Google Script
            payload = {
                "filename": final_name,
                "file": img_str,
                "mimeType": "image/jpeg"
            }
            
            response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
            
            if response.status_code == 200 and "success" in response.text:
                actualizar_interfaz(f"✅ ¡GUARDADA!\n{final_name}", "green")
                nombre_archivo.current.value = ""
                nombre_archivo.current.update()
            else:
                raise Exception("Error en respuesta del servidor")

            if os.path.exists(ruta_local):
                os.remove(ruta_local)

        except Exception as ex:
            actualizar_interfaz(f"❌ Error: {str(ex)}", "red")

    def on_upload_progress(e: ft.FilePickerUploadEvent):
        if e.error:
            actualizar_interfaz(f"Error subida: {e.error}", "red")
        elif e.progress == 1.0:
            procesar_final(e.file_name)

    def iniciar_subida(e: ft.FilePickerResultEvent):
        if not e.files:
            actualizar_interfaz("Listo")
            return
        actualizar_interfaz("⬆️ Procesando archivo...", "orange", True)
        
        files_to_upload = []
        for f in e.files:
            upload_url = page.get_upload_url(f.name, 600)
            files_to_upload.append(ft.FilePickerUploadFile(f.name, upload_url=upload_url))
        file_picker.upload(files_to_upload)

    def abrir_drive(e):
        page.launch_url(f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}")

    def validar_y_abrir_camara(e):
        if not nombre_archivo.current.value.strip():
            nombre_archivo.current.error_text = "⚠️ ¡Pon un nombre primero!"
            page.update()
            return
        
        nombre_archivo.current.error_text = None
        actualizar_interfaz("Abriendo Cámara/Galería...", "blue", True)
        # Cambiado a IMAGE para mayor estabilidad en móviles
        file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)

    file_picker = ft.FilePicker(on_result=iniciar_subida, on_upload=on_upload_progress)
    page.overlay.append(file_picker)

    # --- INTERFAZ ---
    page.add(
        ft.Column([
            ft.Icon(name="cloud_upload", size=60, color="blue"),
            ft.Text("Fotos Cloud", size=30, weight="bold", color="blue"),
            ft.Container(height=10),
            
            ft.TextField(
                ref=nombre_archivo, 
                label="Nombre de la foto", 
                border_color="blue", 
                text_align="center",
                on_submit=validar_y_abrir_camara
            ),
            
            ft.Container(height=10),
            ft.ProgressRing(ref=progreso, visible=False),
            ft.Text(ref=estado_texto, value="Listo", size=14, color="grey", text_align="center"),
            ft.Container(height=10),
            
            ft.ElevatedButton(
                ref=boton_foto,
                text="HACER FOTO / SUBIR", 
                icon="camera_alt", 
                style=ft.ButtonStyle(bgcolor="blue", color="white", padding=20, shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=validar_y_abrir_camara, 
                width=280
            ),
            
            ft.TextButton("Ver Carpeta Drive", icon="folder_open", on_click=abrir_drive),

            ft.Container(height=40),
            ft.Text("Versión 1.1 - Optimizada", size=10, color="grey")
            
        ], alignment="center", horizontal_alignment="center")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)
