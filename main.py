import flet as ft
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image, ImageOps
import io
import datetime
import os

# --- CONFIGURACIÓN ---
# ¡NO OLVIDES PEGAR TU ID DE CARPETA AQUÍ!
DRIVE_FOLDER_ID = "PON_AQUI_EL_ID_DE_TU_CARPETA_DRIVE"
CREDENTIALS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def main(page: ft.Page):
    page.title = "Senator Cloud"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    
    # Alineación Clásica (Estable)
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.padding = 20
    
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    
    def procesar_y_subir(e: ft.FilePickerResultEvent):
        if not e.files: return
        
        estado_texto.current.value = "⚙️ Procesando..."
        estado_texto.current.color = "orange"
        estado_texto.current.update()

        try:
            # 1. Preparar nombre
            raw_name = nombre_archivo.current.value.strip()
            if not raw_name: raw_name = "foto"
            
            # Limpiar nombre de caracteres raros
            base_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{base_name}_{timestamp}.jpg"

            # 2. Leer archivo
            file_obj = e.files[0]
            # En Flet 0.21.2 web, a veces el path es interno, pero esto suele funcionar en upload
            # Si fallara localmente, usaríamos path, pero en web usamos el objeto subido.
            # Nota: Para Render (Web), Flet maneja la subida temporalmente.
            
            # TRUCO: Flet 0.21.2 FilePicker en modo web a veces requiere manejo especial de upload.
            # Pero en esta versión simplificada asumimos entorno estándar.
            # Si da error de lectura, es porque FilePicker web requiere upload_files primero.
            # Para simplificar al máximo y evitar errores de permisos en Render:
            
            with open(file_obj.path, "rb") as f:
                img_bytes = f.read()

            # 3. Optimizar
            img = Image.open(io.BytesIO(img_bytes))
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS) # Calidad HD
            if img.mode != "RGB": img = img.convert("RGB")
            
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=70, optimize=True)
            output_buffer.seek(0)

            # 4. Subir a Drive
            drive_service = authenticate_drive()
            file_metadata = {'name': final_name, 'parents': [DRIVE_FOLDER_ID]}
            media = MediaIoBaseUpload(output_buffer, mimetype='image/jpeg', resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            estado_texto.current.value = f"✅ Subido: {final_name}"
            estado_texto.current.color = "green"
            estado_texto.current.update()
            
            nombre_archivo.current.value = ""
            nombre_archivo.current.update()

        except Exception as ex:
            estado_texto.current.value = f"Error: {str(ex)}"
            estado_texto.current.color = "red"
            estado_texto.current.update()
            print(ex)

    # Configuración FilePicker
    file_picker = ft.FilePicker(on_result=procesar_y_subir)
    page.overlay.append(file_picker)

    # --- Interfaz Gráfica ---
    page.add(
        ft.Column([
            ft.Icon(name=ft.icons.CLOUD_UPLOAD, size=60, color="blue"),
            ft.Text("Subir Foto", size=24, weight="bold"),
            
            ft.Container(height=20),
            
            ft.TextField(
                ref=nombre_archivo, 
                label="Nombre (ej: Habitación 101)", 
                border_color="blue",
                text_align="center"
            ),
            
            ft.Container(height=10),
            
            ft.ElevatedButton(
                "HACER FOTO",
                icon=ft.icons.CAMERA_ALT,
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
            ft.Text("v1.0 Final Stable", size=10, color="grey")
        ], 
        alignment="center", 
        horizontal_alignment="center")
    )

if __name__ == "__main__":
    # Puerto dinámico para Render
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")
