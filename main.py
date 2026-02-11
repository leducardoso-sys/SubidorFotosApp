import flet as ft
import requests
import base64
from PIL import Image, ImageOps
import io
import os
import time

# ==========================================
# 1. CONFIGURACIÓN (Actualiza tus datos aquí)
# ==========================================
MIS_CARPETAS = {
    "Principal": "1NMQDc_8bFfl4s_WVSX7pAKBUhckHRu4v",
    "Instalaciones": "1vGQA_Ry_rMIDKrviYy1MMYw5AVafmrxS",
    "Reparaciones": "1V-dR7JSFTI2jsNxtRgPyFV2Y4rBeYDWp",
}

# Sustituye por tu URL nueva de Google Apps Script
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyYM89KQx19_z1okT1sDJV8FEwYbuZWPTNO8Fih701qgmEMlgBfO3Pj_XEwg8cYCR-LwQ/exec"
TEMP_UPLOAD_DIR = "assets"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

# URL del sonido de confirmación
SFX_SUCCESS = "https://github.com/rafaelconde/escritorio/raw/master/ding.mp3"

def main(page: ft.Page):
    page.title = "Fotos Cloud Pro"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.padding = 20

    # Inicializar audio
    audio_exito = ft.Audio(src=SFX_SUCCESS, autoplay=False)
    page.overlay.append(audio_exito)

    # Recuperar memoria de carpeta
    ultima_carpeta = page.client_storage.get("carpeta_preferida")
    id_inicial = ultima_carpeta if ultima_carpeta in MIS_CARPETAS.values() else list(MIS_CARPETAS.values())[0]

    # Referencias de UI
    nombre_archivo = ft.Ref[ft.TextField]()
    selector_carpeta = ft.Ref[ft.Dropdown]()
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

    def guardar_preferencia(e):
        page.client_storage.set("carpeta_preferida", selector_carpeta.current.value)
        actualizar_interfaz("Carpeta predeterminada actualizada")

    def abrir_drive_actual(e):
        page.launch_url(f"https://drive.google.com/drive/folders/{selector_carpeta.current.value}")

    def procesar_final(nombre_fichero_servidor):
        try:
            actualizar_interfaz("☁️ Subiendo a Drive...", "blue", True)
            
            id_destino = selector_carpeta.current.value
            nombre_destino = next(k for k, v in MIS_CARPETAS.items() if v == id_destino)

            raw_name = nombre_archivo.current.value.strip()
            base_name = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            final_name = f"{base_name if base_name else 'foto'}.jpg"

            ruta_local = os.path.join(TEMP_UPLOAD_DIR, nombre_fichero_servidor)

            # --- PROCESAMIENTO DE IMAGEN ---
            with Image.open(ruta_local) as img:
                img = ImageOps.exif_transpose(img)
                # AJUSTE A 1400px: Ideal para velocidad y calidad en documentos
                img.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
                
                output_buffer = io.BytesIO()
                # Calidad 80: Excelente nitidez
                img.convert("RGB").save(output_buffer, format="JPEG", quality=80, optimize=True)
                img_str = base64.b64encode(output_buffer.getvalue()).decode('utf-8')

            payload = {
                "filename": final_name,
                "file": img_str,
                "mimeType": "image/jpeg",
                "folderId": id_destino
            }
            
            response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=45)
            
            if response.status_code == 200 and "success" in response.text:
                audio_exito.play() # Confirmación sonora
                actualizar_interfaz("✅ ¡SUBIDA CON ÉXITO!", "green")
                
                # Actualizar historial
                nuevo_item = ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color="green", size=16), 
                    ft.Text(f"{final_name} -> {nombre_destino}", size=11)
                ], alignment="center")
                columna_historial.controls.insert(0, nuevo_item)
                if len(columna_historial.controls) > 3: columna_historial.controls.pop()
                
                nombre_archivo.current.value = ""
                nombre_archivo.current.update()
            else:
                raise Exception("Error en respuesta de Drive")

            if os.path.exists(ruta_local): os.remove(ruta_local)

        except Exception as ex:
            actualizar_interfaz(f"❌ Error: {str(ex)}", "red")

    def on_upload_progress(e: ft.FilePickerUploadEvent):
        if e.progress == 1.0:
            time.sleep(0.5)
            procesar_final(e.file_name)

    def iniciar_subida(e: ft.FilePickerResultEvent):
        if not e.files:
            actualizar_interfaz("Listo")
            return
        actualizar_interfaz("⬆️ Cargando archivo...", "orange", True)
        file_picker.upload([ft.FilePickerUploadFile(e.files[0].name, upload_url=page.get_upload_url(e.files[0].name, 600))])

    def validar_y_abrir_camara(e):
        if not nombre_archivo.current.value.strip():
            nombre_archivo.current.error_text = "⚠️ Escribe un nombre primero"
            page.update()
            return
        actualizar_interfaz("Esperando selección...", "blue", True)
        file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.ANY)

    file_picker = ft.FilePicker(on_result=iniciar_subida, on_upload=on_upload_progress)
    page.overlay.append(file_picker)

    # --- DISEÑO ---
    page.add(
        ft.Column([
            ft.Icon(name="cloud_done_rounded", size=60, color="blue"),
            ft.Text("Fotos Cloud Pro", size=28, weight="bold", color="blue"),
            
            ft.Dropdown(
                ref=selector_carpeta,
                label="Carpeta de destino",
                value=id_inicial,
                options=[ft.dropdown.Option(v, k) for k, v in MIS_CARPETAS.items()],
                on_change=guardar_preferencia,
                border_color="blue",
                border_radius=10,
            ),
            
            ft.TextField(ref=nombre_archivo, label="Nombre de la foto", border_color="blue", text_align="center"),
            
            ft.Container(height=10),
            ft.ProgressRing(ref=progreso, visible=False),
            ft.Text(ref=estado_texto, value="Listo para trabajar", size=14, color="grey"),
            
            ft.ElevatedButton(
                ref=boton_foto,
                text="HACER FOTO / SUBIR", 
                icon="camera_alt", 
                style=ft.ButtonStyle(bgcolor="blue", color="white", padding=25, shape=ft.RoundedRectangleBorder(radius=12)),
                on_click=validar_y_abrir_camara, 
                width=300
            ),
            
            ft.TextButton("Abrir Carpeta Actual en Drive", icon="folder_open", on_click=abrir_drive_actual),

            ft.Divider(height=30, thickness=1),
            ft.Text("HISTORIAL RECIENTE", size=12, weight="bold", color="grey700"),
            columna_historial,

            ft.Container(height=40),
            ft.Text("Software Development by Eduardo Cardoso 2026", size=11, color="grey700", weight="bold")
            
        ], alignment="center", horizontal_alignment="center")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, upload_dir=TEMP_UPLOAD_DIR)
