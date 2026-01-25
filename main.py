import flet as ft
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image, ImageOps
import io
import datetime
import os
import shutil

# --- CONFIGURACIÓN ---
DRIVE_FOLDER_ID = "PON_AQUI_EL_ID_DE_TU_CARPETA_DRIVE"
CREDENTIALS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Carpeta temporal en el servidor para recibir la foto del móvil
TEMP_UPLOAD_DIR = "assets"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def main(page: ft.Page):
    page.title = "Senator Cloud"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.padding = 20
    
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    
    # 3. ESTA FUNCIÓN PROCESA LA FOTO CUANDO YA HA LLEGADO AL SERVIDOR
    def procesar_final(nombre_fichero_en_servidor):
        try:
            estado_texto.current.value = "☁️ Enviando a Drive..."
            estado_texto.current.update()

            # Preparar nombre final
            raw_name = nombre_archivo.current.value.strip()
            if not raw_name: raw_name = "foto"
            base_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{base_name}_{timestamp}.jpg"

            # Ruta completa donde ha aterrizado la foto en Render
            ruta_local = os.path.join(TEMP_UPLOAD_DIR, nombre_fichero_en_servidor)

            # Optimizar
            img = Image.open(ruta_local)
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            if img.mode != "RGB": img = img.convert("RGB")
            
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=70, optimize=True)
            output_buffer.seek(0)

            # Subir a Google Drive
            drive_service = authenticate_drive()
            file_metadata = {'name': final_name, 'parents': [DRIVE_FOLDER_ID]}
            media = MediaIoBaseUpload(output_buffer, mimetype='image/jpeg', resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            # Limpieza y Éxito
            estado_texto.current.value = f"✅ ÉXITO: {final_name}"
            estado_texto.current.color = "green"
            estado_texto.current.update()
            
            nombre_archivo.current.value = ""
            nombre_archivo.current.update()
            
            # Borrar archivo temporal del servidor para no llenar disco
            os.remove(ruta_local)

        except Exception as ex:
            estado_texto.current.value = f"❌ Error Drive: {str(ex)}"
            estado_texto.current.color = "red"
            estado_texto.current.update()
            print(ex)

    # 2. DETECTAR CUANDO TERMINA LA SUBIDA DEL MÓVIL AL SERVIDOR
    def on_upload_progress(e: ft.FilePickerUploadEvent):
        # Cuando el progreso es 1.0 (100%) o hay error
        if e.error:
            estado_texto.current.value = f"Error subida: {e.error}"
            estado_texto.current.update()
            return
            
        if e.progress == 1.0:
            # La foto ya está en Render. Ahora la procesamos.
            procesar_final(e.file_name)

    # 1. CUANDO SELECCIONAS LA FOTO (INICIA LA SUBIDA)
    def iniciar_subida(e: ft.FilePickerResultEvent):
        if not e.files: return
        
        estado_texto.current.value = "⬆️ Subiendo al servidor..."
        estado_texto.current.color = "orange"
        estado_texto.current.update()
        
        # Obtenemos el archivo seleccionado y lo subimos a Render
        # Esto soluciona el error "NoneType" porque no intentamos leerlo directo
        file_picker.upload(e.files)

    # Configuración FilePicker
    file_picker = ft.FilePicker(
        on_result=iniciar_subida, 
        on_upload=on_upload_progress
    )
    page.overlay.append(file_picker)

    # --- UI ---
    page.add(
        ft.Column([
            ft.Icon(name="cloud_upload", size=60, color="blue"),
            ft.Text("Subir Foto", size=24, weight="bold"),
            
            ft.Container(height=20),
            
            ft.TextField(
                ref=nombre_archivo, 
                label="Nombre (ej: Baño 101)", 
                border_color="blue",
                text_align="center"
            ),
            
            ft.Container(height=10),
            
            ft.ElevatedButton(
                "HACER FOTO",
                icon="camera_alt",
                style=ft.ButtonStyle(
                    bgcolor="blue",
                    color="white",
                    padding=20,
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
                on_click=lambda _: file_picker.pick_files(
                    allow_multiple=False, 
                    file_type=ft.FilePickerFileType.IMAGE
                ),
                width=280
            ),
            
            ft.Container(height=20),
            ft.Text(ref=estado_texto, value="Listo", size=14, color="grey"),
            ft.Container(height=20),
            ft.Text("v11.0 Upload Fix", size=10, color="grey")
        ], 
        alignment="center", 
        horizontal_alignment="center")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # IMPORTANTE: upload_dir="assets" define dónde aterrizan las fotos
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0", upload_dir=TEMP_UPLOAD_DIR)
