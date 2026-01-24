import flet as ft
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image, ImageOps
import io
import datetime

# --- CONFIGURACIÓN ---
# ID de la carpeta de Google Drive (es la parte rara del final de la URL de tu carpeta)
# Ejemplo: drive.google.com/drive/folders/1A2B3C4D5E6F... -> El ID es "1A2B3C4D5E6F..."
DRIVE_FOLDER_ID = "PON_AQUI_EL_ID_DE_TU_CARPETA_DRIVE"

# Nombre del archivo de credenciales (debe estar junto a este script)
CREDENTIALS_FILE = "credentials.json"

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def main(page: ft.Page):
    page.title = "Senator Cloud Uploader"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Variables de estado
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    
    def procesar_y_subir(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        
        estado_texto.current.value = "⚙️ Optimizando y subiendo..."
        estado_texto.current.color = "orange"
        estado_texto.current.update()

        try:
            # 1. Preparar nombre
            base_name = nombre_archivo.current.value.strip() or "foto"
            base_name = "".join([c for c in base_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{base_name}_{timestamp}.jpg"

            # 2. Leer archivo en memoria (sin guardar en disco del servidor)
            file_obj = e.files[0]
            
            # Flet devuelve la ruta o los bytes dependiendo del entorno.
            # Leemos los bytes del archivo subido
            with open(file_obj.path, "rb") as f:
                img_bytes = f.read()

            # 3. Optimización con Pillow en memoria
            img = Image.open(io.BytesIO(img_bytes))
            img = ImageOps.exif_transpose(img) # Corregir rotación
            img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Guardar la imagen optimizada en un buffer de memoria (RAM)
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=70, optimize=True)
            output_buffer.seek(0) # Volver al inicio del buffer para leerlo

            # 4. SUBIR A GOOGLE DRIVE
            drive_service = authenticate_drive()
            
            file_metadata = {
                'name': final_name,
                'parents': [DRIVE_FOLDER_ID]
            }
            
            media = MediaIoBaseUpload(output_buffer, mimetype='image/jpeg', resumable=True)
            
            drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            estado_texto.current.value = f"✅ ¡Subido a Drive!\n{final_name}"
            estado_texto.current.color = "green"
            estado_texto.current.update()
            
            # Limpiar campo (opcional)
            nombre_archivo.current.value = ""
            nombre_archivo.current.update()

        except Exception as ex:
            estado_texto.current.value = f"❌ Error: {str(ex)}"
            estado_texto.current.color = "red"
            estado_texto.current.update()
            print(ex)

    file_picker = ft.FilePicker(on_result=procesar_y_subir)
    page.overlay.append(file_picker)

    # --- UI ---
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.CLOUD_CIRCLE, size=60, color=ft.colors.BLUE_600),
                ft.Text("Subir a Drive", size=24, weight="bold"),
                ft.Divider(),
                ft.TextField(
                    ref=nombre_archivo,
                    label="Nombre (ej: Habitación 101)",
                    border_color=ft.colors.BLUE_400
                ),
                ft.Container(height=10),
                ft.ElevatedButton(
                    "HACER FOTO",
                    icon=ft.icons.CAMERA_ALT,
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.BLUE_600, 
                        color="white", 
                        padding=20,
                        shape=ft.RoundedRectangleBorder(radius=8)
                    ),
                    on_click=lambda _: file_picker.pick_files(
                        allow_multiple=False, 
                        file_type=ft.FilePickerFileType.IMAGE
                    ),
                    width=280
                ),
                ft.Container(height=20),
                ft.Text(ref=estado_texto, value="Listo", size=14, text_align="center"),
                ft.Container(height=30),
                ft.Text("v2.0 Cloud Drive", size=10, color="grey")
            ], horizontal_alignment="center"),
            padding=20,
            alignment=ft.alignment.center
        )
    )

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080, host="0.0.0.0")