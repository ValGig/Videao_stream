import os
import pandas as pd
from pytubefix import YouTube, Search
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import signal
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

# Fonction de recherche d'une vidéo YouTube
def search_video(query):
    print("Recherche de vidéos pour:", query)
    search_results = Search(query).videos
    return search_results

# Fonction pour télécharger l'audio
def download_audio(video):
    print("Téléchargement de l'audio...")
    streams = video.streams.filter(only_audio=True, file_extension='webm') 
    if streams:
        stream = streams.order_by('abr').desc().first()
        print(f"Codec : {stream.codecs} \nBitrate : {stream.abr} kbps\nFormat : {stream.mime_type}\nTaille : {stream.filesize/1000000} Mo\n")
        audio_file = stream.download(output_path="Downloads", filename=f"{video.title}.webm")
        return audio_file
    else:
        print("Aucun flux audio disponible.")
        return None

# Fonction pour jouer l'audio avec VLC
def play_audio_vlc(audio_file, start_time=0, on_finish=None):
    global vlc_process, current_audio_file, playback_start_time, is_playing

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

# Fonction pour basculer Play/Pause
def toggle_play_pause():
    global is_playing, vlc_process, audio_position, playback_start_time

    if is_playing:
        print("Mise en pause...")
        audio_position = time.time() - playback_start_time  # Sauvegarder la position actuelle
        if vlc_process:
            vlc_process.terminate()  # Arrêter VLC quand en pause
        is_playing = False
    else:
        print(f"Reprise à {audio_position:.2f} secondes...")
        play_audio_vlc(current_audio_file, audio_position)  # Reprendre à la position de la pause
        is_playing = True

# Fonction pour la lecture d'une piste de playlist
def play_song(index):
    global current_index, is_playing
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

def next_track():
    global current_index, is_playing
    if current_playlist is not None and current_index < len(current_playlist) - 1:
        current_index += 1
        is_playing = True  # Forcer l'état "playing" pour la nouvelle piste
        play_song(current_index)  # Appeler play_song pour la piste suivante
    else:
        print("Fin de la playlist.")
        is_playing = False  # Mettre is_playing à False à la fin de la playlist

def prev_track():
    global current_index
    if current_playlist is not None and current_index > 0:
        current_index -= 1
        play_song(current_index)

def play_selected_track(*args):
    """Lance la lecture de la piste sélectionnée dans le menu déroulant."""
    global current_playlist, track_menu_var
    selected_track = track_menu_var.get()
    if selected_track and current_playlist is not None:
        index = current_playlist[current_playlist['title'] == selected_track].index[0]
        play_song(index)

def load_selected_playlist(playlist_name):
    """Charge une playlist et met à jour le menu déroulant des pistes."""
    global current_playlist, current_index, track_menu_var
    try:
        playlist_path = os.path.join(playlists_folder, playlist_name)
        current_playlist = pd.read_csv(playlist_path, header=None, names=['title'])
        current_index = 0

        # Mettre à jour le menu des titres
        track_menu_var.set(current_playlist.iloc[0]['title'])
        track_dropdown['values'] = current_playlist['title'].tolist()

        # Lancer la lecture de la première piste
        play_song(current_index)
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur de chargement:\n{str(e)}")

def perform_search(query):
    global search_results_list, search_results_listbox
    if not query:
        return
    
    search_results = search_video(query)
    search_results_list = search_results
    search_results_listbox.delete(0, tk.END)
    for result in search_results:
        search_results_listbox.insert(tk.END, result.title)

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

def stop_vlc():
    """Fonction pour arrêter VLC lorsque l'application se ferme."""
    global vlc_process
    if vlc_process:
        vlc_process.terminate()
        vlc_process.wait()  # Attendre que le processus VLC soit terminé
    print("VLC arrêté.")

def handle_exit():
    """Fonction de gestion de la fermeture du programme."""
    stop_vlc()
    root.quit()

# Enregistrer la fonction de gestion de la fermeture avec atexit
atexit.register(stop_vlc)

def main_gui():
    global root, playpause_button, title_label, track_dropdown, track_menu_var, search_results_listbox

    root = tk.Tk()
    root.title('Lecteur Audio')
    root.config(bg='#303030')

    # Définir la fonction de fermeture
    root.protocol("WM_DELETE_WINDOW", handle_exit)  # Arrêter VLC lors de la fermeture de la fenêtre

    # Cadre principal pour la partie haute
    top_frame = tk.Frame(root, bg='#303030')
    top_frame.pack(fill='both', expand=True)

    # Section One-shot (gauche)
    left_frame = tk.Frame(top_frame, bg='#303030')
    left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)

    # Titre "Rechercher une piste" (centré et en gras)
    search_label = tk.Label(left_frame, text="Rechercher une piste", bg='#303030', fg='white', font=('Helvetica', 12, 'bold'))
    search_label.grid(row=0, column=0, pady=10, sticky='ew')

    # Champ de recherche
    search_entry = tk.Entry(left_frame, width=50, bg='#303030', fg='white')
    search_entry.grid(row=1, column=0, pady=5, sticky='ew')

    # Bouton de recherche
    search_button = tk.Button(left_frame, text="Rechercher", command=lambda: perform_search(search_entry.get()), bg='#ee6020', fg='black')
    search_button.grid(row=2, column=0, pady=5, sticky='ew')

    # Liste des résultats de recherche
    search_results_listbox = tk.Listbox(left_frame, width=50, height=5, bg='#303030', fg='white')
    search_results_listbox.grid(row=3, column=0, pady=5, sticky='ew')

    # Bouton pour lire la piste sélectionnée
    play_selected_button = tk.Button(left_frame, text="Lire la piste sélectionnée", command=play_selected_search_result, bg='#ee6020', fg='black')
    play_selected_button.grid(row=4, column=0, pady=5, sticky='ew')

    # Espace entre les parties gauche et droite
    separator = tk.Frame(top_frame, bg='white', width=1.5)
    separator.pack(side='left', fill='y', padx=10)

    # Section Playlist (droite)
    right_frame = tk.Frame(top_frame, bg='#303030')
    right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)

    # Titre "Gestion des playlists" (centré et en gras)
    playlist_label = tk.Label(right_frame, text="Gestion des playlists", bg='#303030', fg='white', font=('Helvetica', 12, 'bold'))
    playlist_label.grid(row=0, column=0, pady=10, sticky='ew')

    # Menu déroulant pour sélectionner une playlist
    playlists = [f for f in os.listdir(playlists_folder) if f.endswith('.txt')]
    selected_playlist = tk.StringVar(value=playlists[0] if playlists else "")
    playlist_menu = ttk.Combobox(right_frame, textvariable=selected_playlist, values=playlists, state='readonly', width=47)
    playlist_menu.grid(row=1, column=0, pady=5, sticky='ew')

    # Bouton pour charger la playlist
    load_button = tk.Button(right_frame, text="Charger la playlist", command=lambda: load_selected_playlist(selected_playlist.get()), bg='#ee6020', fg='black')
    load_button.grid(row=2, column=0, pady=5, sticky='ew')

    # Menu déroulant pour sélectionner une piste dans la playlist
    track_menu_var = tk.StringVar()
    track_dropdown = ttk.Combobox(right_frame, textvariable=track_menu_var, state='readonly', width=47)
    track_dropdown.grid(row=3, column=0, pady=5, sticky='ew')

    # Associer la sélection d'une piste à la fonction play_selected_track
    track_menu_var.trace_add('write', play_selected_track)

    # Bouton pour lancer la lecture de la piste sélectionnée dans la playlist
    play_button = tk.Button(right_frame, text="Lire la piste", command=play_selected_track, bg='#ee6020', fg='black')
    play_button.grid(row=4, column=0, pady=5, sticky='ew')

    # Contrôles (partie basse)
    bottom_frame = tk.Frame(root, bg='#303030')
    bottom_frame.pack(fill='x', pady=10)

    # Centrer les boutons de navigation et le titre
    control_frame = tk.Frame(bottom_frame, bg='#303030')
    control_frame.pack(side='top')

    prev_button = tk.Button(control_frame, text="Précédent", command=prev_track, bg='#cc5080', fg='white')
    prev_button.pack(side='left', padx=5)

    global playpause_button
    playpause_button = tk.Button(control_frame, text="Play/Pause", command=toggle_play_pause, bg='#aa50aa', fg='white')
    playpause_button.pack(side='left', padx=5)

    next_button = tk.Button(control_frame, text="Suivant", command=next_track, bg='#8050cc', fg='white')
    next_button.pack(side='left', padx=5)

    # Titre de la piste jouée
    title_label = tk.Label(bottom_frame, text="", font=("Helvetica", 12), bg='#303030', fg='white')
    title_label.pack(side='top', pady=10)

    # Charger la première playlist si disponible
    if playlists:
        load_selected_playlist(playlists[0])

    root.mainloop()


if __name__ == "__main__":
    if not os.path.exists(playlists_folder):
        os.makedirs(playlists_folder)
    main_gui()
