import os
import pandas as pd
from pytubefix import YouTube, Search
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import atexit

# Dossier pour les playlists
playlists_folder = 'Playlists'

# Variables globales
vlc_process = None
is_playing = False
current_audio_file = None
audio_position = 0
current_playlist = None
current_index = 0
playback_start_time = 0
search_results_list = []
progress_bar = None
total_duration = 0  # Durée totale de la piste en secondes

# Fonction de recherche d'une vidéo YouTube
def search_video(query):
    print("Recherche de vidéos pour:", query)
    search_results = Search(query).videos
    return search_results

# Fonction pour télécharger l'audio
def download_audio(video):
    print("Téléchargement de l'audio...")
    
    try:
        # Essayer de récupérer le flux audio en webm
        streams = video.streams.filter(only_audio=True, file_extension='webm')
        if streams:
            stream = streams.order_by('abr').desc().first()
            print(f"Codec : {stream.codecs} \nBitrate : {stream.abr} kbps\nFormat : {stream.mime_type}\nTaille : {stream.filesize / 1000000} Mo\n")
            audio_file = stream.download(output_path="Downloads", filename=f"{video.title}.webm")
            return audio_file
        else:
            print("Aucun flux audio en webm disponible. Tentative avec mp4...")
            
            # Si aucun flux webm n'est trouvé, tenter de télécharger en mp4
            streams_mp4 = video.streams.filter(only_audio=True, file_extension='mp4')
            if streams_mp4:
                stream_mp4 = streams_mp4.order_by('abr').desc().first()
                print(f"Codec : {stream_mp4.codecs} \nBitrate : {stream_mp4.abr} kbps\nFormat : {stream_mp4.mime_type}\nTaille : {stream_mp4.filesize / 1000000} Mo\n")
                audio_file = stream_mp4.download(output_path="Downloads", filename=f"{video.title}.mp4")
                return audio_file
            else:
                print("Aucun flux audio en mp4 disponible non plus.")
                return None
    except Exception as e:
        print(f"Erreur lors du téléchargement de l'audio : {str(e)}")
        return None

# Fonction pour jouer l'audio avec VLC
def play_audio_vlc(audio_file, start_time=0, on_finish=None):
    global vlc_process, current_audio_file, playback_start_time, is_playing, progress_bar, total_duration

    current_audio_file = audio_file

    # Si un processus VLC est déjà en cours, on l'arrête
    if vlc_process:
        vlc_process.terminate()
        vlc_process.wait()  # Attendre que le processus soit complètement terminé

    playback_start_time = time.time() - start_time
    try:
        vlc_process = subprocess.Popen(
            ['vlc', '--intf', 'dummy', '--play-and-exit', '--start-time', str(start_time), audio_file],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )
    except Exception as e:
        print(f"Impossible de lancer VLC: {str(e)}")
        return

    current_process = vlc_process

    # Vérification rapide du démarrage
    time.sleep(0.2)
    if current_process.poll() is not None:
        print("Échec du démarrage de VLC. Fichier corrompu?")
        return

    def monitor_process(process):
        global is_playing
        process.wait()
        exit_code = process.poll()
        print(f"Processus VLC terminé avec le code de sortie : {exit_code}")

        # Si la lecture s'est bien terminée, réinitialiser l'état et appeler le callback on_finish
        if vlc_process == process and is_playing and exit_code == 0:
            is_playing = False
            if on_finish:
                print("Appel du callback on_finish...")
                time.sleep(0.1)  # Petit délai pour éviter les conflits de thread
                on_finish()  # Appeler le callback pour passer à la piste suivante
        elif exit_code != 0:
            print(f"Erreur de lecture (code {exit_code})")

    # Démarrer un thread pour surveiller le processus
    threading.Thread(target=monitor_process, args=(current_process,), daemon=True).start()

    # Démarrer un thread pour mettre à jour la barre de progression
    threading.Thread(target=update_progress_bar, daemon=True).start()

# Fonction pour mettre à jour la barre de progression
def update_progress_bar():
    global vlc_process, progress_bar, playback_start_time, is_playing, total_duration

    while is_playing and vlc_process and vlc_process.poll() is None:
        current_time = time.time() - playback_start_time
        if total_duration > 0:
            progress_bar['value'] = current_time
        time.sleep(1)  # Mettre à jour la barre de progression toutes les secondes

# Fonction pour basculer Play/Pause
def toggle_play_pause():
    global is_playing, vlc_process, audio_position, playback_start_time

    if is_playing:
        audio_position = time.time() - playback_start_time  # Sauvegarder la position actuelle
        print(f"Mise en pause à {audio_position:.2f} secondes...")
        if vlc_process:
            vlc_process.terminate()  # Arrêter VLC quand en pause
        is_playing = False
    else:
        print(f"Reprise à {audio_position:.2f} secondes...")
        play_audio_vlc(current_audio_file, audio_position)  # Reprendre à la position de la pause
        is_playing = True

# Fonction pour la lecture d'une piste de playlist
def play_song(index):
    global current_index, is_playing, total_duration
    if current_playlist is None or index < 0 or index >= len(current_playlist):
        return

    current_index = index
    song_title = current_playlist.iloc[index]['title']
    search_results = search_video(song_title)

    if not search_results:
        messagebox.showerror("Erreur", "Aucun résultat trouvé!")
        return

    try:
        video = YouTube(search_results[0].watch_url)
        total_duration = video.length  # Récupérer la durée totale de la piste
        progress_bar['to'] = total_duration  # Ajuster la barre de progression
        audio_file = download_audio(video)
        if audio_file:
            title_label.config(text=video.title)
            is_playing = True  # Forcer l'état "playing" pour la lecture
            threading.Thread(
                target=lambda: play_audio_vlc(audio_file, on_finish=next_track),  # Passer next_track ici pour l'enchaînement
                daemon=True
            ).start()
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur de lecture:\n{str(e)}")

# Fonction pour passer à la piste suivante
def next_track():
    global current_index, is_playing
    if current_playlist is not None and current_index < len(current_playlist) - 1:
        current_index += 1
        is_playing = True  # Forcer l'état "playing" pour la nouvelle piste
        play_song(current_index)  # Appeler play_song pour la piste suivante
    else:
        print("Fin de la playlist.")
        is_playing = False  # Mettre is_playing à False à la fin de la playlist

# Fonction pour revenir à la piste précédente
def prev_track():
    global current_index
    if current_playlist is not None and current_index > 0:
        current_index -= 1
        play_song(current_index)

# Fonction pour jouer la piste sélectionnée dans le menu déroulant
def play_selected_track(*args):
    global current_playlist, track_menu_var
    selected_track = track_menu_var.get()
    if selected_track and current_playlist is not None:
        index = current_playlist[current_playlist['title'] == selected_track].index[0]
        play_song(index)

# Fonction pour charger une playlist
def load_selected_playlist(playlist_name):
    global current_playlist, current_index, track_menu_var
    try:
        playlist_path = os.path.join(playlists_folder, playlist_name)
        current_playlist = pd.read_csv(playlist_path, header=None, names=['title'])
        current_index = 0

        # Mettre à jour le menu des titres
        track_menu_var.set(current_playlist.iloc[0]['title'])
        track_dropdown['values'] = current_playlist['title'].tolist()

        # Lancer la lecture de la première piste
        #play_song(current_index)
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur de chargement:\n{str(e)}")

# Fonction pour effectuer une recherche
def perform_search(query):
    global search_results_list, search_results_listbox
    if not query:
        return

    search_results = search_video(query)
    search_results_list = search_results
    search_results_listbox.delete(0, tk.END)
    for result in search_results:
        search_results_listbox.insert(tk.END, result.title)

# Fonction pour jouer la piste sélectionnée dans les résultats de recherche
def play_selected_search_result():
    global search_results_list
    selected_indices = search_results_listbox.curselection()
    if not selected_indices:
        messagebox.showerror("Erreur", "Aucune vidéo sélectionnée!")
        return

    index = selected_indices[0]
    chosen_video = search_results_list[index]

    try:
        video = YouTube(chosen_video.watch_url)
        total_duration = video.length  # Récupérer la durée totale de la piste
        progress_bar['to'] = total_duration  # Ajuster la barre de progression
        audio_file = download_audio(video)
        if audio_file:
            title_label.config(text=video.title)
            global is_playing, current_audio_file
            current_audio_file = audio_file
            is_playing = True
            threading.Thread(
                target=lambda: play_audio_vlc(audio_file),
                daemon=True
            ).start()
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur de lecture:\n{str(e)}")

# Fonction pour se déplacer dans la piste
def seek_track(value):
    global vlc_process, is_playing, current_audio_file, playback_start_time, total_duration

    if is_playing and vlc_process:
        new_position = float(value)  # Nouvelle position en secondes
        if new_position < total_duration:  # Vérifier que la position est valide
            vlc_process.terminate()
            vlc_process.wait()
            play_audio_vlc(current_audio_file, start_time=new_position)

# Fonction pour arrêter VLC
def stop_vlc():
    global vlc_process
    if vlc_process:
        vlc_process.terminate()
        vlc_process.wait()  # Attendre que le processus VLC soit terminé
    print("VLC arrêté.")

# Fonction de gestion de la fermeture du programme
def handle_exit():
    stop_vlc()
    root.quit()

# Enregistrer la fonction de gestion de la fermeture avec atexit
atexit.register(stop_vlc)

# Fonction principale pour l'interface graphique
def main_gui():
    global root, playpause_button, title_label, track_dropdown, track_menu_var, search_results_listbox, progress_bar

    root = tk.Tk()
    root.title('Lecteur Audio')
    root.config(bg='#2b2b2b')

    # Créer le style personnalisé
    style = ttk.Style()
    style.theme_create('custom', parent='alt', settings={
        'TCombobox': {
            'configure': {
                'fieldbackground': '#2b2b2b',
                'background': '#2b2b2b',
                'foreground': 'white',
                'arrowcolor': 'white',
                'selectbackground': '#303030',
                'selectforeground': 'white'
            }
        },
        'Horizontal.TScale': {
            'configure': {
                'troughcolor': '#404040',  # Couleur de la piste
                'background': '#2b2b2b',  # Couleur de fond
                'bordercolor': '#f36f28',  # Couleur de la bordure
                'lightcolor': '#f36f28',  # Couleur de la lumière (effet 3D)
                'darkcolor': '#f36f28',  # Couleur de l'ombre (effet 3D)
                'sliderthickness': 10,  # Épaisseur du curseur
                'sliderrelief': 'flat'  # Style du curseur
            }
        }
    })
    style.theme_use('custom')

    # Définir la fonction de fermeture
    root.protocol("WM_DELETE_WINDOW", handle_exit)  # Arrêter VLC lors de la fermeture de la fenêtre

    # Cadre principal pour la partie haute
    top_frame = tk.Frame(root, bg='#2b2b2b')
    top_frame.pack(fill='both', expand=True)

    # Section One-shot (gauche)
    left_frame = tk.Frame(top_frame, bg='#2b2b2b')
    left_frame.pack(side='left', fill='both', expand=True, padx=20, pady=20)

    # Titre "Rechercher une piste"
    search_label = tk.Label(left_frame, text="Rechercher une piste", bg='#2b2b2b', fg='white', font=('Helvetica', 14, 'bold'))
    search_label.grid(row=0, column=0, pady=10, sticky='ew')

    # Champ de recherche
    search_entry = tk.Entry(left_frame, width=50, bg='#2b2b2b', fg='white')
    search_entry.grid(row=1, column=0, pady=5, sticky='ew')

    # Bouton de recherche
    search_button = tk.Button(left_frame, text="Rechercher", command=lambda: perform_search(search_entry.get()), bg='#f36f28', fg='black', relief='flat', font=('Arial', 10, 'bold'))
    search_button.grid(row=2, column=0, pady=5, sticky='ew')

    # Liste des résultats de recherche
    search_results_listbox = tk.Listbox(left_frame, width=50, height=5, bg='#2b2b2b', fg='white')
    search_results_listbox.grid(row=3, column=0, pady=5, sticky='ew')

    # Bouton pour lire la piste sélectionnée
    play_selected_button = tk.Button(left_frame, text="Lire la piste sélectionnée", command=play_selected_search_result, bg='#f36f28', fg='black', relief='flat', font=('Arial', 10, 'bold'))
    play_selected_button.grid(row=4, column=0, pady=5, sticky='ew')

    # Séparateur entre la partie gauche et droite
    separator = tk.Frame(top_frame, bg='white', width=1.5)
    separator.pack(side='left', fill='y', padx=20)

    # Partie Playlist (droite)
    right_frame = tk.Frame(top_frame, bg='#2b2b2b')
    right_frame.pack(side='right', fill='both', expand=True, padx=20, pady=20)

    # Titre "Gestion des playlists"
    playlist_label = tk.Label(right_frame, text="Gestion des playlists", bg='#2b2b2b', fg='white', font=('Helvetica', 14, 'bold'))
    playlist_label.grid(row=0, column=0, pady=10, sticky='ew')

    # Menu déroulant pour sélectionner une playlist
    playlists = [f for f in os.listdir(playlists_folder) if f.endswith('.txt')]
    selected_playlist = tk.StringVar(value=playlists[0] if playlists else "")
    playlist_menu = ttk.Combobox(right_frame, textvariable=selected_playlist, values=playlists, state='readonly', width=47)
    playlist_menu.grid(row=1, column=0, pady=5, sticky='ew')

    # Bouton pour charger la playlist
    load_button = tk.Button(right_frame, text="Charger la playlist", command=lambda: load_selected_playlist(selected_playlist.get()), bg='#f36f28', fg='black', relief='flat', font=('Arial', 10, 'bold'))
    load_button.grid(row=2, column=0, pady=5, sticky='ew')

    # Menu déroulant pour sélectionner une piste dans la playlist
    track_menu_var = tk.StringVar()
    track_dropdown = ttk.Combobox(right_frame, textvariable=track_menu_var, state='readonly', width=47)
    track_dropdown.grid(row=3, column=0, pady=5, sticky='ew')

    # Associer la sélection d'une piste à la fonction play_selected_track
    track_menu_var.trace_add('write', play_selected_track)

    # Bouton pour lancer la lecture de la piste sélectionnée
    play_button = tk.Button(right_frame, text="Lire la piste", command=play_selected_track, bg='#f36f28', fg='black', relief='flat', font=('Arial', 10, 'bold'))
    play_button.grid(row=4, column=0, pady=5, sticky='ew')

    # Contrôles (partie basse)
    bottom_frame = tk.Frame(root, bg='#2b2b2b')
    bottom_frame.pack(fill='x', pady=10)

    # Centrer les boutons de navigation et le titre
    control_frame = tk.Frame(bottom_frame, bg='#2b2b2b')
    control_frame.pack(side='top')

    prev_button = tk.Button(control_frame, text="|<<", command=prev_track, bg='#cc5080', fg='white', relief='flat', font=('Arial', 10, 'bold'))
    prev_button.pack(side='left', padx=5)

    global playpause_button
    playpause_button = tk.Button(control_frame, text="Play/Pause", command=toggle_play_pause, bg='#a35da6', fg='white', relief='flat', font=('Arial', 10, 'bold'))
    playpause_button.pack(side='left', padx=5)

    next_button = tk.Button(control_frame, text=">>|", command=next_track, bg='#8b53cc', fg='white', relief='flat', font=('Arial', 10, 'bold'))
    next_button.pack(side='left', padx=5)

    # Titre de la piste jouée
    title_label = tk.Label(bottom_frame, text="", font=("Helvetica", 12), bg='#2b2b2b', fg='white')
    title_label.pack(side='top', pady=10)

    # Barre de progression personnalisée
    progress_bar = ttk.Scale(bottom_frame, from_=0, to=100, orient='horizontal', command=seek_track, style="Custom.Horizontal.TScale")
    progress_bar.pack(side='top', fill='x', padx=20, pady=10)

    # Charger la première playlist si disponible
    if playlists:
        load_selected_playlist(playlists[0])

    root.mainloop()

if __name__ == "__main__":
    main_gui()