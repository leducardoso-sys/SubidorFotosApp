import flet as ft
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image, ImageOps
import io
import datetime
import os

# --- CONFIGURACIÓN ---
DRIVE_FOLDER_ID = "PON_AQUI_EL_ID_DE_TU_CARPETA_DRIVE"
CREDENTIALS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def main(page: ft.Page):
    page.title = "Senator Cloud Uploader"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    
    # Alineación de la página completa
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    nombre_archivo = ft.Ref[ft.TextField]()
    estado_texto = ft.Ref[ft.Text]()
    
    # Función de subida
    def procesar_y_subir(e):
        if not e.files: return
        
        estado_texto.current.value = "⚙️ Optimizando y subiendo..."
        estado_texto.current.color = "orange"
        estado_texto.current.update()

        try:
            base_name = nombre_archivo.current.value.strip() or "foto"
            base_name = "".join([c for c in base_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{base_name}_{timestamp}.jpg"

            file_obj = e.files[0]
            with open(file_obj.path, "rb") as f: img_bytes = f.read()

            img = Image.open(io.BytesIO(img_bytes))
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            if img.mode != "RGB": img = img.convert("RGB")
            
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=70, optimize=True)
            output_buffer.seek(0)

            drive_service = authenticate_drive()
            file_metadata = {'name': final_name, 'parents': [DRIVE_FOLDER_ID]}
            media = MediaIoBaseUpload(output_buffer, mimetype='image/jpeg', resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            estado_texto.current.value = f"✅ ¡Subido a Drive!\n{final_name}"
            estado_texto.current.color = "green"
            estado_texto.current.update()
            
            nombre_archivo.current.value = ""
            nombre_archivo.current.update()

        except Exception as ex:
            estado_texto.current.value = f"❌ Error: {str(ex)}"
            estado_texto.current.color = "red"
            estado_texto.current.update()
            print(ex)

    # Configuración del selector de archivos
    file_picker = ft.FilePicker()
    file_picker.on_result = procesar_y_subir
    page.overlay.append(file_picker)

    # --- UI ---
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Icon("cloud_upload", size=60, color="blue"),
                
                ft.Text("Subir a Drive", size=24, weight="bold"),
                ft.Divider(),
                
                ft.TextField(ref=nombre_archivo, label="Nombre (ej: Habitación 101)", border_color="blue"),
                
                ft.Container(height=10),
                
                # Nota: Mantenemos ElevatedButton aunque avise de "deprecated"
                # porque funciona bien y cambiarlo a Button() requiere cambiar todos los estilos.
                # El aviso (warning) no romperá la app.
                ft.ElevatedButton(
                    "HACER FOTO", 
                    icon="camera_alt", 
                    style=ft.ButtonStyle(
                        bgcolor="blue", 
                        color="white", 
                        padding=20, 
                        shape=ft.RoundedRectangleBorder(radius=8)
                    ), 
                    on_click=lambda _: file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE), 
                    width=280
                ),
                ft.Container(height=20),
                ft.Text(ref=estado_texto, value="Listo", size=14, text_align="center"),
                ft.Container(height=30),
                ft.Text("v6.0 Alignment Fix", size=10, color="grey")
            ], 
            # Alineación de la columna interna
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            
            padding=20,
            # CORRECCIÓN AQUÍ: Usamos ft.Alignment(0,0) en lugar de ft.alignment.center
            # (0,0) significa centro matemático. Esto no falla nunca.
            alignment=ft.Alignment(0, 0)
        )
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")
