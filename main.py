import flet as ft
import requests
import base64
from PIL import Image, ImageOps
import io
import os
import time

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
    
    # Referencias de UI
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    boton_foto = ft.Ref[ft.ElevatedButton]()
    progreso = ft.Ref[ft.ProgressRing]()
    columna_historial = ft.Column(horizontal_alignment="center", spacing=5)

    def actualizar_interfaz(texto, color="grey", ocupado=False):
        estado_texto.current.value = texto
        estado_texto.current.color = color
        progreso.current.visible = ocupado
        boton_foto.current.disabled = ocupado
        page.update()

    def agregar_al_historial(nombre):
        # Insertar al principio y mantener solo los últimos 3
        nuevo_item = ft.Row(
            [ft.Icon(ft.icons.CHECK_CIRCLE, color="green", size=16), ft.Text(nombre, size=12)],
            alignment="center"
        )
        columna_historial.controls.insert(0, nuevo_item)
        if len(columna_historial.controls) > 3:
            columna_historial.controls.pop()
        page.update()

    # --- LÓGICA DE PROCESAMIENTO ---
    def procesar_final(nombre_fichero_servidor):
        try:
            if not nombre_fichero_servidor.lower().endswith(('.png', '.jpg', '.jpeg', '.heic')):
                 actualizar_interfaz("⚠️ Error: Solo imágenes.", "red")
                 return

            actualizar_interfaz("☁️ Subiendo a Drive...", "blue", True)

            raw_name = nombre_archivo.current.value.strip()
            base_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            if not base_name: base_name = "foto_sin_nombre"
            final_name = f"{base_name}.jpg"

            ruta_local = os.path.join(TEMP_UPLOAD_DIR, nombre_fichero_servidor)

            with Image.open(ruta_local) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                if img.mode != "RGB": img = img.convert("RGB")
                
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="JPEG", quality=65, optimize=True)
                img_str = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

            payload = {
                "filename": final_name,
                "file": img_str,
                "mimeType": "image/jpeg"
            }
            
            response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=45)
            
            if response.status_code == 200 and "success" in response.text:
                actualizar_interfaz(f"✅ ¡ÉXITO!", "green")
                agregar_al_historial(final_name)
                nombre_archivo.current.value = ""
                nombre_archivo.current.update()
            else:
                raise Exception("Error en Google Drive")

            if os.path.exists(ruta_local):
                os.remove(ruta_local)

        except Exception as ex:
            actualizar_interfaz(f"❌ Error: {str(ex)}", "red")

    def on_upload_progress(e: ft.FilePickerUploadEvent):
        if e.error:
            actualizar_interfaz(f"Error: {e.error}", "red")
        elif e.progress == 1.0:
            time.sleep(0.5)
            procesar_final(e.file_name)

    def iniciar_subida(e: ft.FilePickerResultEvent):
        if not e.files:
            actualizar_interfaz("Listo para disparar")
            return
        actualizar_interfaz("⬆️ Cargando...", "orange", True)
        for f in e.files:
            upload_url = page.get_upload_url(f.name, 600)
            file_picker.upload([ft.FilePickerUploadFile(f.name, upload_url=upload_url)])

    def abrir_drive(e):
        page.launch_url(f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}")

    def validar_y_abrir_camara(e):
        if not nombre_archivo.current.value.strip():
            nombre_archivo.current.error_text = "⚠️ Escribe un nombre primero"
            page.update()
            return
        
        nombre_archivo.current.error_text = None
        actualizar_interfaz("Abriendo menú...", "blue", True)
        file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.ANY)

    file_picker = ft.FilePicker(on_result=iniciar_subida, on_upload=on_upload_progress)
    page.overlay.append(file_picker)

    # --- DISEÑO ---
    page.add(
        ft.Column([
            ft.Icon(name="cloud_upload_rounded", size=70, color="blue"),
            ft.Text("Fotos Cloud", size=28, weight="bold", color="blue"),
            
            ft.Container(height=15),
            
            ft.TextField(
                ref=nombre_archivo, 
                label="Nombre de la foto", 
                border_radius=10,
                border_color="blue", 
                text_align="center",
                # on_submit eliminado para evitar apertura automática
            ),
            
            ft.Container(height=10),
            ft.ProgressRing(ref=progreso, visible=False),
            ft.Text(ref=estado_texto, value="Listo para disparar", size=14, color="grey"),
            
            ft.ElevatedButton(
                ref=boton_foto,
                text="ABRIR CÁMARA", 
                icon="camera_alt", 
                style=ft.ButtonStyle(bgcolor="blue", color="white", padding=25, shape=ft.RoundedRectangleBorder(radius=12)),
                on_click=validar_y_abrir_camara, 
                width=300
            ),
            
            ft.Container(height=10),
            ft.TextButton("Ver Carpeta Drive", icon="folder_shared", on_click=abrir_drive),

            ft.Divider(height=40, thickness=1),
            
            ft.Text("HISTORIAL RECIENTE", size=12, weight="bold", color="grey700"),
            columna_historial,

            ft.Container(height=30),
            ft.Text("v1.3 - Historial y flujo corregido", size=10, color="grey")
            
        ], alignment="center", horizontal_alignment="center")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, upload_dir=TEMP_UPLOAD_DIR)
