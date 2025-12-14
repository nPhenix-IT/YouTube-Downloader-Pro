import flet as ft
import yt_dlp
import os
import threading
import platform
import time

# --- Système de Traduction Simplifié (FR/EN) ---
TRANSLATIONS = {
    "fr": {
        "window_title": "YouTube Downloader PRO",
        "url_label": "Lien (Vidéo/Playlist)",
        "analyze_btn": "ANALYSER",
        "col_left_title": "Vidéos",
        "select_all": "Tout cocher",
        "no_video": "Aucune vidéo",
        "col_right_title": "Options",
        "format_label": "Format",
        "quality_label": "Qualité",
        "dl_mp4_btn": "TÉLÉCHARGER",
        "dl_mp3_btn": "AUDIO SEUL (M4A)",
        "waiting": "En attente...",
        "pause_state": "PAUSE",
        "finished": "Terminé !",
        "folder_label": "Sauvegardé dans Downloads",
        "analyzing": "Analyse...",
        "videos_found": "{} vidéos",
        "error": "Erreur : {}",
        "error_private": "Vidéo privée/inaccessible détectée.",
        "skipped": "Ignorée...",
        "processing": "{} / {}"
    },
    "en": {
        "window_title": "YouTube Downloader PRO",
        "url_label": "Link (Video/Playlist)",
        "analyze_btn": "ANALYZE",
        "col_left_title": "Videos",
        "select_all": "Select All",
        "no_video": "No video",
        "col_right_title": "Options",
        "format_label": "Format",
        "quality_label": "Quality",
        "dl_mp4_btn": "DOWNLOAD",
        "dl_mp3_btn": "AUDIO ONLY (M4A)",
        "waiting": "Waiting...",
        "pause_state": "PAUSED",
        "finished": "Done!",
        "folder_label": "Saved in Downloads",
        "analyzing": "Analyzing...",
        "videos_found": "{} videos",
        "error": "Error: {}",
        "error_private": "Private/Unavailable video detected.",
        "skipped": "Skipped...",
        "processing": "{} / {}"
    }
}

# Langue par défaut
current_lang = "fr"

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
    # --- Configuration Mobile ---
    page.title = tr("window_title")
    page.theme_mode = "dark"
    page.padding = 10
    # Sur mobile, on active le scroll car le clavier peut masquer des éléments
    page.scroll = "auto" 
    
    # Pas de dimensions fixes sur mobile
    page.vertical_alignment = "start"
    page.horizontal_alignment = "center"

    # --- Variables d'état ---
    # Chemin standard Android pour les téléchargements publics
    try:
        if platform.system() == "Android":
            from android.storage import primary_external_storage_path
            dir = primary_external_storage_path()
            download_path = os.path.join(dir, 'Download')
        else:
            # Fallback pour test sur PC
            download_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    except:
        download_path = "/storage/emulated/0/Download"

    if not os.path.exists(download_path):
        try: os.makedirs(download_path)
        except: pass

    current_state = DownloadState.IDLE
    video_list_data = []
    download_queue = []
    current_video_index = 0

    # --- UI : Header ---
    title_text = ft.Text(tr("window_title"), size=20, weight="bold")
    
    url_input = ft.TextField(
        label=tr("url_label"),
        prefix_icon="link",
        border_radius=10,
        height=45,
        text_size=14,
        expand=True
    )

    analyze_btn = ft.IconButton(
        icon="search",
        icon_color="white",
        bgcolor="blue",
        on_click=lambda e: analyze_button_click(e)
    )

    search_area = ft.Row([url_input, analyze_btn], alignment="center")

    # --- UI : Liste Vidéos ---
    videos_list_view = ft.ListView(height=150, spacing=5, padding=5) # Hauteur fixe pour scroller dedans
    select_all_checkbox = ft.Checkbox(label=tr("select_all"), value=True, on_change=lambda e: toggle_select_all(e))
    list_info_text = ft.Text(tr("no_video"), color="grey", italic=True, size=12)

    list_container = ft.Container(
        content=ft.Column([
            ft.Text(tr("col_left_title"), weight="bold"),
            select_all_checkbox,
            list_info_text,
            videos_list_view
        ]),
        border=ft.border.all(1, "grey"),
        border_radius=10,
        padding=10,
        visible=False # Caché au départ
    )

    # --- UI : Options & Actions ---
    
    def on_format_change(e):
        if format_dropdown.value == "AUDIO":
            start_download_btn.text = tr("dl_mp3_btn")
            start_download_btn.icon = "audiotrack"
        else:
            start_download_btn.text = tr("dl_mp4_btn")
            start_download_btn.icon = "download"
        page.update()

    format_dropdown = ft.Dropdown(
        label=tr("format_label"),
        expand=True,
        text_size=14,
        options=[
            ft.dropdown.Option("MP4"),
            ft.dropdown.Option("AUDIO"), # On évite "MP3" car conversion impossible sans ffmpeg binaire
        ],
        value="MP4",
        on_change=on_format_change
    )

    options_row = ft.Row([format_dropdown], alignment="center")

    start_download_btn = ft.ElevatedButton(
        text=tr("dl_mp4_btn"),
        icon="download",
        bgcolor="green",
        color="white",
        height=50,
        width=200,
        on_click=lambda e: start_download_sequence(e)
    )

    current_video_label = ft.Text(tr("waiting"), weight="bold", size=12, text_align="center")
    progress_bar = ft.ProgressBar(width=200, value=0, color="blue", bgcolor="grey") 
    
    # Indicateurs compacts pour mobile
    status_row = ft.Row(
        [
            ft.Text("-", size=10, color="grey", ref=lambda x: setattr(x, 'key', 'speed')), # Fake ref
            ft.Text("-", size=10, color="grey", ref=lambda x: setattr(x, 'key', 'eta'))
        ], 
        alignment="space_between", width=200
    )
    # On garde des références manuelles pour mise à jour
    speed_text = status_row.controls[0]
    eta_text = status_row.controls[1]

    btn_cancel = ft.IconButton(icon="stop", icon_size=30, icon_color="red", on_click=lambda e: set_state(DownloadState.CANCELLED))
    
    controls_column = ft.Column(
        [
            ft.Divider(),
            ft.Text(tr("col_right_title"), weight="bold"),
            options_row,
            ft.Container(height=10),
            start_download_btn,
            ft.Container(height=10),
            current_video_label,
            progress_bar,
            status_row,
            ft.Container(height=10),
            btn_cancel,
            ft.Text(tr("folder_label"), size=10, color="grey")
        ],
        horizontal_alignment="center",
        visible=False # Caché au départ
    )

    # --- Logique Métier ---

    def set_state(new_state):
        nonlocal current_state
        current_state = new_state
        page.update()

    def analyze_button_click(e):
        url = url_input.value
        if not url: return

        analyze_btn.disabled = True
        list_info_text.value = tr("analyzing")
        videos_list_view.controls.clear()
        
        list_container.visible = True
        page.update()

        threading.Thread(target=run_analyze, args=(url,), daemon=True).start()

    def run_analyze(url):
        nonlocal video_list_data
        # Sur mobile, on veut être léger
        ydl_opts = {'extract_flat': True, 'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info: video_list_data = list(info['entries'])
                else: video_list_data = [info]
            
            videos_list_view.controls.clear()
            for vid in video_list_data:
                title = vid.get('title', 'Sans titre')
                # Gestion ID vs URL selon playlist ou video
                vid_id = vid.get('id')
                vid_url = vid.get('url')
                final_url = vid_url if vid_url and "youtube" in vid_url else f"https://www.youtube.com/watch?v={vid_id}"

                cb = ft.Checkbox(label=title, value=True, data=final_url)
                videos_list_view.controls.append(cb)

            list_info_text.value = tr("videos_found", len(video_list_data))
            analyze_btn.disabled = False
            controls_column.visible = True
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

        if d['status'] == 'downloading':
            try:
                p = d.get('_percent_str', '0%').replace('%', '')
                try:
                    progress_bar.value = float(p) / 100
                except: pass

                current_video_label.value = f"{d.get('_percent_str', '')}"
                speed_text.value = d.get('_speed_str', '-')
                eta_text.value = d.get('_eta_str', '-')
                page.update()
            except: pass

    def run_download_loop():
        nonlocal current_video_index, current_state
        
        selected_format = format_dropdown.value

        while current_video_index < len(download_queue):
            if current_state == DownloadState.CANCELLED: break

            # Récupération de l'objet Checkbox
            current_checkbox_item = download_queue[current_video_index]
            url = current_checkbox_item.data

            # --- UI : EN COURS (⏩) ---
            clean_title = current_checkbox_item.label.replace("⏩ ", "").replace("✔️ ", "").replace("❌ ", "")
            current_checkbox_item.label = f"⏩ {clean_title}"
            current_checkbox_item.update()

            current_video_label.value = tr("processing", current_video_index + 1, len(download_queue))
            progress_bar.value = 0 
            page.update()

            # CONFIGURATION CRITIQUE POUR ANDROID
            ydl_opts = {
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
                'noplaylist': True,
                # Important: ignorer les erreurs SSL sur certains vieux androids
                'nocheckcertificate': True,
                'ignoreerrors': True,
                # Force le client 'default' (Android/iOS)
                'extractor_args': {'youtube': {'player_client': ['default']}}
            }

            if selected_format == "AUDIO":
                # On prend le meilleur audio dispo (souvent m4a), pas de conversion mp3
                ydl_opts.update({'format': 'bestaudio/best'})
            else:
                # On prend le meilleur fichier qui contient DEJA video+audio (souvent 720p ou 360p max)
                ydl_opts.update({'format': 'best[ext=mp4]'})

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # --- SUCCÈS : MISE A JOUR UI LISTE (✔️) ---
                current_checkbox_item.value = False
                current_checkbox_item.label = f"✔️ {clean_title}"
                current_checkbox_item.update()

                current_video_index += 1
            except Exception as e:
                # --- ÉCHEC : MISE A JOUR UI LISTE (❌) ---
                current_checkbox_item.value = False
                current_checkbox_item.label = f"❌ {clean_title}"
                current_checkbox_item.update()

                print(f"Erreur DL: {e}")
                if "CANCELLED" in str(e):
                    break
                
                # Gestion erreur Private video sur mobile
                error_msg = str(e)
                if "Private video" in error_msg or "Sign in" in error_msg:
                    current_video_label.value = f"{tr('error_private')} {tr('skipped')}"
                else:
                    current_video_label.value = f"Erreur. {tr('skipped')}"
                page.update()
                time.sleep(1)

                current_video_index += 1 

        current_video_label.value = tr("finished")
        start_download_btn.disabled = False
        analyze_btn.disabled = False
        page.update()

    def start_download_sequence(e):
        nonlocal download_queue, current_video_index
        download_queue = []
        for ctrl in videos_list_view.controls:
            if isinstance(ctrl, ft.Checkbox) and ctrl.value:
                # On stocke l'objet entier pour le modifier
                download_queue.append(ctrl)
        
        if not download_queue: return

        current_video_index = 0
        set_state(DownloadState.RUNNING)
        
        start_download_btn.disabled = True
        analyze_btn.disabled = True
        
        page.update()
        threading.Thread(target=run_download_loop, daemon=True).start()

    # --- Assemblage ---
    page.add(
        ft.Column([
            ft.Row([ft.Icon("video_library", color="red"), title_text], alignment="center"),
            ft.Divider(height=10, color="transparent"),
            search_area,
            ft.Divider(height=10),
            list_container,
            controls_column
        ])
    )

if __name__ == "__main__":
    ft.app(target=main)
