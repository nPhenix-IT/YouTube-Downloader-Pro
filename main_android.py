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
        "folder_label": "Dossier : {}",
        "analyzing": "Analyse...",
        "videos_found": "{} vidéos",
        "error": "Erreur : {}",
        "error_private": "Vidéo privée/inaccessible.",
        "error_perm": "Permission refusée -> Tentative dossier secours...",
        "fallback_ok": "Sauvegardé dans dossier privé (Android/data)",
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
        "folder_label": "Folder: {}",
        "analyzing": "Analyzing...",
        "videos_found": "{} videos",
        "error": "Error: {}",
        "error_private": "Private/Unavailable video.",
        "error_perm": "Permission denied -> Trying fallback folder...",
        "fallback_ok": "Saved in private folder (Android/data)",
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
    page.scroll = "auto" 
    page.vertical_alignment = "start"
    page.horizontal_alignment = "center"

    # --- Variables d'état ---
    # Stratégie de dossiers : Public d'abord, Privé en secours
    public_download_path = "/storage/emulated/0/Download"
    # Chemin privé spécifique à l'app (toujours accessible sans permission)
    # Note : "com.example.apk_project" correspond au package par défaut de flet create
    private_download_path = "/storage/emulated/0/Android/data/com.example.apk_project/files"

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
    videos_list_view = ft.ListView(height=150, spacing=5, padding=5) 
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
        visible=False 
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
            ft.dropdown.Option("AUDIO"), 
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
    current_video_label.no_wrap = False 
    
    progress_bar = ft.ProgressBar(width=200, value=0, color="blue", bgcolor="grey") 
    
    status_row = ft.Row(
        [
            ft.Text("-", size=10, color="grey", ref=lambda x: setattr(x, 'key', 'speed')), 
            ft.Text("-", size=10, color="grey", ref=lambda x: setattr(x, 'key', 'eta'))
        ], 
        alignment="space_between", width=200
    )
    speed_text = status_row.controls[0]
    eta_text = status_row.controls[1]

    btn_cancel = ft.IconButton(icon="stop", icon_size=30, icon_color="red", on_click=lambda e: set_state(DownloadState.CANCELLED))
    
    folder_info_text = ft.Text(tr("folder_label", "..."), size=10, color="grey")

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
            folder_info_text
        ],
        horizontal_alignment="center",
        visible=False 
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
        ydl_opts = {'extract_flat': True, 'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info: video_list_data = list(info['entries'])
                else: video_list_data = [info]
            
            videos_list_view.controls.clear()
            for vid in video_list_data:
                title = vid.get('title', 'Sans titre')
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
        
        # Choix initial du dossier (Public)
        target_dir = public_download_path
        folder_info_text.value = tr("folder_label", "Download (Public)")
        page.update()

        while current_video_index < len(download_queue):
            if current_state == DownloadState.CANCELLED: break

            current_checkbox_item = download_queue[current_video_index]
            url = current_checkbox_item.data

            # --- UI : EN COURS (⏩) ---
            clean_title = current_checkbox_item.label.replace("⏩ ", "").replace("✔️ ", "").replace("❌ ", "")
            current_checkbox_item.label = f"⏩ {clean_title}"
            current_checkbox_item.update()

            current_video_label.value = tr("processing", current_video_index + 1, len(download_queue))
            current_video_label.color = "white"
            progress_bar.value = 0 
            page.update()

            # Configuration de base
            ydl_opts = {
                'outtmpl': os.path.join(target_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
                'noplaylist': True,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'extractor_args': {'youtube': {'player_client': ['default']}}
            }

            if selected_format == "AUDIO":
                ydl_opts.update({'format': 'bestaudio/best'})
            else:
                ydl_opts.update({'format': 'best[ext=mp4]'})

            success = False
            
            # TENTATIVE 1 : Dossier Public
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                success = True
            except Exception as e:
                error_msg = str(e)
                # Si erreur de permission, on tente le dossier privé
                if "Permission denied" in error_msg or "EACCES" in error_msg or "OSError" in error_msg:
                    current_video_label.value = tr("error_perm")
                    current_video_label.color = "orange"
                    page.update()
                    time.sleep(1)
                    
                    # TENTATIVE 2 : Dossier Privé (Secours)
                    try:
                        # On crée le dossier privé si besoin
                        if not os.path.exists(private_download_path):
                            os.makedirs(private_download_path, exist_ok=True)
                        
                        target_dir = private_download_path
                        ydl_opts['outtmpl'] = os.path.join(target_dir, '%(title)s.%(ext)s')
                        folder_info_text.value = tr("folder_label", "Android/data/... (Private)")
                        page.update()
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                        
                        success = True
                        current_video_label.value = tr("fallback_ok")
                        time.sleep(1)
                        
                    except Exception as e2:
                        print(f"Echec fallback: {e2}")
                        success = False
                
                elif "CANCELLED" in error_msg:
                    break
                else:
                    success = False # Autre erreur (ex: video privée)

            # Résultat Final pour cet élément
            if success:
                current_checkbox_item.value = False
                current_checkbox_item.label = f"✔️ {clean_title}"
                current_checkbox_item.update()
            else:
                current_checkbox_item.value = False
                current_checkbox_item.label = f"❌ {clean_title}"
                current_checkbox_item.update()
                # Si l'erreur n'est pas déjà affichée
                if current_video_label.color != "orange":
                    current_video_label.value = f"Erreur."
                    current_video_label.color = "red"
                    page.update()
                    time.sleep(1.5)

            current_video_index += 1 

        current_video_label.value = tr("finished")
        current_video_label.color = "green"
        start_download_btn.disabled = False
        analyze_btn.disabled = False
        page.update()

    def start_download_sequence(e):
        nonlocal download_queue, current_video_index
        download_queue = []
        for ctrl in videos_list_view.controls:
            if isinstance(ctrl, ft.Checkbox) and ctrl.value:
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
