import flet as ft
import yt_dlp
import os
import threading
import time
import imageio_ffmpeg
import platform
import locale
import subprocess # Nécessaire pour macOS (langue et ouverture dossier)
import ctypes # Nécessaire pour détecter la langue sur Windows

# --- Système de Traduction ---
# Dictionnaire contenant tous les textes en FR et EN
TRANSLATIONS = {
    "fr": {
        "window_title": "YouTube Downloader Pro",
        "url_label": "Collez le lien ici (Vidéo ou Playlist)",
        "analyze_btn": "ANALYSER",
        "col_left_title": "1. Sélectionnez les vidéos",
        "select_all": "Tout sélectionner",
        "no_video": "Aucune vidéo chargée",
        "col_right_title": "2. Options & Progression",
        "format_label": "Format",
        "quality_label": "Qualité",
        "dl_mp4_btn": "TÉLÉCHARGER MP4",
        "dl_mp3_btn": "CONVERTIR EN MP3",
        "waiting": "En attente...",
        "pause_state": "PAUSE",
        "finished": "Terminé !",
        "folder_label": "Dossier de sortie : ",
        "open_folder_btn": "OUVRIR LE DOSSIER",
        "analyzing": "Analyse en cours...",
        "videos_found": "{} vidéos trouvées",
        "error": "Erreur : {}",
        "processing": "Traitement {}/{}..."
    },
    "en": {
        "window_title": "YouTube Downloader Pro",
        "url_label": "Paste link here (Video or Playlist)",
        "analyze_btn": "ANALYZE",
        "col_left_title": "1. Select Videos",
        "select_all": "Select All",
        "no_video": "No video loaded",
        "col_right_title": "2. Options & Progress",
        "format_label": "Format",
        "quality_label": "Quality",
        "dl_mp4_btn": "DOWNLOAD MP4",
        "dl_mp3_btn": "CONVERT TO MP3",
        "waiting": "Waiting...",
        "pause_state": "PAUSED",
        "finished": "Done!",
        "folder_label": "Output folder: ",
        "open_folder_btn": "OPEN FOLDER",
        "analyzing": "Analyzing...",
        "videos_found": "{} videos found",
        "error": "Error: {}",
        "processing": "Processing {}/{}..."
    }
}

# --- Détection Avancée de la Langue ---
def get_system_language():
    """
    Détecte la langue de l'interface utilisateur en fonction de l'OS.
    Retourne 'fr' ou 'en'.
    """
    os_name = platform.system()
    detected_lang = "en" # Langue par défaut (anglais)

    try:
        if os_name == "Windows":
            # Sur Windows, on utilise l'API système via ctypes pour être précis
            windll = ctypes.windll.kernel32
            # Récupère l'ID de langue utilisateur (ex: 1036 pour FR Standard)
            lang_id = windll.GetUserDefaultUILanguage()
            # Le masque 0x3FF permet de récupérer l'ID primaire de la langue
            # 0x0C (12) correspond au Français (toutes régions confondues)
            if (lang_id & 0x3FF) == 0x0C:
                detected_lang = "fr"
        
        elif os_name == "Darwin": # macOS
            # Sur Mac, le module locale est souvent cassé. On lit la config Apple.
            # On interroge la liste des langues préférées
            cmd = "defaults read -g AppleLanguages"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            output = result.stdout
            
            # La sortie est une liste textuelle : ( "fr-FR", "en-US", ... )
            # On vérifie simplement si "fr" apparaît dans les premiers caractères
            if output:
                # On nettoie un peu pour regarder le début de la liste
                head = output.strip().replace('\n', '').replace(' ', '')[:30]
                if '"fr' in head: # Cherche "fr... dans la première entrée
                    detected_lang = "fr"
        
        else:
            # Linux / Autre : On utilise la méthode standard locale
            sys_locale = locale.getdefaultlocale()[0]
            if sys_locale and sys_locale.startswith("fr"):
                detected_lang = "fr"

    except Exception as e:
        print(f"Erreur détection langue ({e}), fallback sur EN.")

    return detected_lang

# Initialisation de la langue
current_lang = get_system_language()

# Fonction helper pour récupérer le texte traduit
def tr(key, *args):
    text = TRANSLATIONS[current_lang].get(key, key)
    if args:
        return text.format(*args)
    return text

# --- Configuration Globale ---
class DownloadState:
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    IDLE = "idle"

def main(page: ft.Page):
    # --- Configuration de la fenêtre ---
    page.title = tr("window_title")
    page.theme_mode = "dark"
    
    # Dimensions cibles ajustées (plus compactes)
    width = 700
    height = 550

    page.window_width = width
    page.window_height = height
    
    # --- VERROUILLAGE STRICT (Fixe) ---
    page.window_min_width = width
    page.window_max_width = width
    page.window_min_height = height
    page.window_max_height = height
    
    page.window_resizable = False 
    page.window_maximizable = False
    
    page.vertical_alignment = "start"
    page.horizontal_alignment = "center"
    page.padding = 20

    # --- Variables d'état ---
    home = os.path.expanduser('~')
    download_path = os.path.join(home, tr("window_title")) 
    if not os.path.exists(download_path):
        try: os.makedirs(download_path)
        except: download_path = os.path.join(home, tr("window_title"))

    current_state = DownloadState.IDLE
    video_list_data = []
    download_queue = []
    current_video_index = 0

    # --- UI : Zone Recherche (Haut de page) ---
    title_text = ft.Text(tr("window_title"), size=24, weight="bold")
    
    url_input = ft.TextField(
        label=tr("url_label"),
        expand=True,
        prefix_icon="link",
        border_radius=10,
        height=45,
        content_padding=10,
        text_size=14,
        on_submit=lambda e: analyze_button_click(e)
    )

    analyze_btn = ft.ElevatedButton(
        text=tr("analyze_btn"),
        icon="search",
        height=45,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=lambda e: analyze_button_click(e)
    )

    search_area = ft.Row([url_input, analyze_btn], alignment="center")

    # --- UI : Colonne Gauche (Liste) ---
    videos_list_view = ft.ListView(expand=True, spacing=5, padding=10, auto_scroll=False)
    select_all_checkbox = ft.Checkbox(label=tr("select_all"), value=True, on_change=lambda e: toggle_select_all(e))
    list_info_text = ft.Text(tr("no_video"), color="grey", italic=True, size=12)

    left_column = ft.Column(
        [
            ft.Text(tr("col_left_title"), weight="bold", size=16),
            ft.Divider(height=10),
            select_all_checkbox,
            list_info_text,
            ft.Container(
                content=videos_list_view,
                expand=True, 
                border=ft.border.all(1, "grey"),
                border_radius=10,
                padding=5
            )
        ],
        expand=True
    )

    # --- UI : Colonne Droite (Contrôles & Progression) ---
    
    def on_format_change(e):
        if format_dropdown.value == "MP3":
            resolution_dropdown.visible = False
            start_download_btn.text = tr("dl_mp3_btn")
            start_download_btn.icon = "audiotrack"
        else:
            resolution_dropdown.visible = True
            start_download_btn.text = tr("dl_mp4_btn")
            start_download_btn.icon = "download"
        page.update()

    format_dropdown = ft.Dropdown(
        label=tr("format_label"),
        width=130,
        text_size=14,
        options=[
            ft.dropdown.Option("MP4"),
            ft.dropdown.Option("MP3"),
        ],
        value="MP4",
        border_radius=10,
        prefix_icon="file_present",
        on_change=on_format_change
    )

    resolution_dropdown = ft.Dropdown(
        label=tr("quality_label"),
        width=130,
        text_size=14,
        options=[
            ft.dropdown.Option("1080p"),
            ft.dropdown.Option("720p"),
            ft.dropdown.Option("480p"),
            ft.dropdown.Option("360p"),
            ft.dropdown.Option("240p"),
        ],
        value="480p",
        border_radius=10,
        prefix_icon="settings"
    )

    options_row = ft.Row([format_dropdown, resolution_dropdown], alignment="center")

    start_download_btn = ft.ElevatedButton(
        text=tr("dl_mp4_btn"),
        icon="download",
        bgcolor="green",
        color="white",
        height=45,
        width=280,
        disabled=True, 
        on_click=lambda e: start_download_sequence(e)
    )

    # NOUVEAU BOUTON : Ouvrir le dossier
    open_folder_btn = ft.ElevatedButton(
        text=tr("open_folder_btn"),
        icon="folder_open",
        bgcolor="blue",
        color="white",
        height=45,
        width=280,
        visible=False, # Caché par défaut
        on_click=lambda e: open_destination_folder()
    )

    current_video_label = ft.Text(tr("waiting"), weight="bold", size=14, text_align="center")
    progress_bar = ft.ProgressBar(width=300, value=0, color="blue", bgcolor="grey") 
    speed_text = ft.Text("-", size=11, color="grey")
    eta_text = ft.Text("-", size=11, color="grey")
    
    btn_pause = ft.IconButton(icon="pause", icon_size=24, icon_color="orange", tooltip="Pause", on_click=lambda e: set_state(DownloadState.PAUSED))
    btn_resume = ft.IconButton(icon="play_arrow", icon_size=24, icon_color="green", tooltip="Resume", visible=False, on_click=lambda e: resume_download(e))
    btn_cancel = ft.IconButton(icon="stop", icon_size=24, icon_color="red", tooltip="Stop", on_click=lambda e: set_state(DownloadState.CANCELLED))
    
    controls_row = ft.Row([btn_pause, btn_resume, btn_cancel], alignment="center", visible=False)

    right_column = ft.Column(
        [
            ft.Text(tr("col_right_title"), weight="bold", size=16),
            ft.Divider(height=10),
            ft.Container(height=5),
            
            options_row,
            
            ft.Container(height=10),
            start_download_btn,
            # open_folder_btn a été déplacé en bas
            ft.Container(height=20), 
            
            ft.Container(
                content=ft.Column([
                    current_video_label,
                    ft.Container(height=5),
                    progress_bar,
                    ft.Row([speed_text, eta_text], alignment="space_between", width=300)
                ], horizontal_alignment="center"),
                padding=15,
                bgcolor="#222222", 
                border_radius=10,
                width=340
            ),
            
            ft.Container(height=10),
            controls_row,
            ft.Container(height=10), # Espace avant le bouton dossier
            open_folder_btn, # Emplacement modifié : juste avant le texte
            ft.Container(height=5),
            ft.Text(tr("folder_label") + download_path, size=10, color="grey", text_align="center")
        ],
        horizontal_alignment="center",
        expand=True
    )

    main_content = ft.Row(
        [
            ft.Container(content=left_column, expand=1, padding=10),
            ft.VerticalDivider(width=1, color="grey"),
            ft.Container(content=right_column, expand=1, padding=10)
        ],
        expand=True,
        visible=False 
    )

    # --- Logique Métier ---

    def open_destination_folder():
        """Ouvre le dossier de téléchargement selon l'OS"""
        path = download_path
        try:
            sys_os = platform.system()
            if sys_os == "Windows":
                os.startfile(path)
            elif sys_os == "Darwin": # macOS
                subprocess.Popen(["open", path])
            else: # Linux
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"Erreur ouverture dossier: {e}")

    def play_finish_sound():
        try:
            sys_os = platform.system()
            if sys_os == "Darwin":
                os.system('afplay /System/Library/Sounds/Glass.aiff')
            elif sys_os == "Windows":
                import winsound
                winsound.MessageBeep()
            else:
                print('\a')
        except Exception as e:
            print(f"Impossible de jouer le son: {e}")

    def set_state(new_state):
        nonlocal current_state
        current_state = new_state
        
        if new_state == DownloadState.PAUSED:
            btn_pause.visible = False
            btn_resume.visible = True
            current_video_label.value = tr("pause_state")
            current_video_label.color = "orange"
        elif new_state == DownloadState.RUNNING:
            btn_pause.visible = True
            btn_resume.visible = False
            current_video_label.color = "white"
        
        page.update()

    def analyze_button_click(e):
        url = url_input.value
        if not url: return

        analyze_btn.disabled = True
        list_info_text.value = tr("analyzing")
        videos_list_view.controls.clear()
        
        main_content.visible = True
        start_download_btn.disabled = True
        page.update()

        threading.Thread(target=run_analyze, args=(url,), daemon=True).start()

    def run_analyze(url):
        nonlocal video_list_data
        ydl_opts = {'extract_flat': True, 'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info: video_list_data = list(info['entries'])
                else: video_list_data = [info]
            
            videos_list_view.controls.clear()
            for vid in video_list_data:
                title = vid.get('title', 'Sans titre')
                vid_url = vid.get('url') if 'entries' not in info else f"https://www.youtube.com/watch?v={vid['id']}"
                cb = ft.Checkbox(label=title, value=True, data=vid_url)
                videos_list_view.controls.append(cb)

            list_info_text.value = tr("videos_found", len(video_list_data))
            analyze_btn.disabled = False
            start_download_btn.disabled = False
            page.update()

        except Exception as e:
            list_info_text.value = tr("error", str(e))
            analyze_btn.disabled = False
            page.update()

    def toggle_select_all(e):
        for ctrl in videos_list_view.controls:
            if isinstance(ctrl, ft.Checkbox): ctrl.value = select_all_checkbox.value
        page.update()

    def progress_hook(d):
        if current_state == DownloadState.CANCELLED: raise Exception("CANCELLED")
        if current_state == DownloadState.PAUSED: raise Exception("PAUSED")

        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                
                percent_str = "0%"
                
                if total:
                    ratio = downloaded / total
                    progress_bar.value = ratio
                    percent_str = f"{int(ratio * 100)}%"
                else:
                    p = d.get('_percent_str', '0%').replace('%', '')
                    import re
                    ansi_escape = re.compile(r'\x1b[^m]*m')
                    p = ansi_escape.sub('', p)
                    try:
                        progress_bar.value = float(p) / 100
                        percent_str = f"{p}%"
                    except: pass

                current_video_label.value = f"Downloading : {percent_str}"
                speed_text.value = f"Speed: {d.get('_speed_str', '-')}"
                eta_text.value = f"ETA: {d.get('_eta_str', '-')}"
                page.update()
            except Exception as e: 
                pass

    def run_download_loop():
        nonlocal current_video_index, current_state
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        selected_format = format_dropdown.value
        res_value = resolution_dropdown.value.replace("p", "")

        while current_video_index < len(download_queue):
            if current_state == DownloadState.CANCELLED: break
            if current_state == DownloadState.PAUSED: break

            url = download_queue[current_video_index]
            current_video_label.value = tr("processing", current_video_index + 1, len(download_queue))
            progress_bar.value = 0 
            page.update()

            ydl_opts = {
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
                'ffmpeg_location': ffmpeg_path,
                'noplaylist': True,
            }

            if selected_format == "MP3":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                format_string = f'bestvideo[height<={res_value}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res_value}][ext=mp4]/best[height<={res_value}]'
                ydl_opts.update({
                    'format': format_string,
                })

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                current_video_index += 1
                progress_bar.value = 1 
                page.update()
            except Exception as e:
                if "PAUSED" in str(e): return
                elif "CANCELLED" in str(e):
                    reset_ui_after_download()
                    return
                else:
                    current_video_index += 1 

        if current_video_index >= len(download_queue):
            current_video_label.value = tr("finished")
            play_finish_sound()
            reset_ui_after_download()

    def start_download_sequence(e):
        nonlocal download_queue, current_video_index
        download_queue = []
        for ctrl in videos_list_view.controls:
            if isinstance(ctrl, ft.Checkbox) and ctrl.value:
                download_queue.append(ctrl.data)
        
        if not download_queue: return

        current_video_index = 0
        set_state(DownloadState.RUNNING)
        
        # UI Updates
        start_download_btn.disabled = True # On désactive au lieu de cacher
        open_folder_btn.visible = False 
        
        resolution_dropdown.disabled = True 
        format_dropdown.disabled = True 
        controls_row.visible = True
        analyze_btn.disabled = True
        url_input.disabled = True
        videos_list_view.disabled = True 
        select_all_checkbox.disabled = True
        
        page.update()
        threading.Thread(target=run_download_loop, daemon=True).start()

    def resume_download(e):
        set_state(DownloadState.RUNNING)
        threading.Thread(target=run_download_loop, daemon=True).start()

    def reset_ui_after_download():
        nonlocal current_state
        current_state = DownloadState.IDLE
        controls_row.visible = False
        
        start_download_btn.visible = True # On s'assure qu'il est visible
        start_download_btn.disabled = False # On réactive
        open_folder_btn.visible = True 
        
        resolution_dropdown.disabled = False 
        format_dropdown.disabled = False 
        analyze_btn.disabled = False
        url_input.disabled = False
        videos_list_view.disabled = False
        select_all_checkbox.disabled = False
        progress_bar.value = 0
        speed_text.value = "-"
        eta_text.value = "-"
        page.update()

    # --- Assemblage final ---
    page.add(
        ft.Column([
            ft.Row([ft.Icon("video_library", size=40, color="red"), title_text], alignment="center"),
            ft.Divider(color="transparent", height=10),
            search_area,
            ft.Divider(),
            main_content 
        ], expand=True)
    )

if __name__ == "__main__":
    ft.app(target=main)