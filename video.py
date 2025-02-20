import os
import pandas as pd
from pytubefix import YouTube
from pytube import Search
import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import time

# Dossier pour les playlists
playlists_folder = 'Playlists'

# Variables globales
ffplay_process = None
is_playing = False
current_audio_file = None
audio_position = 0
current_playlist = None
current_index = 0

# Fonction de recherche d'une vidéo YouTube
def search_video(query):
    print("Recherche de vidéos pour:", query)
    search_results = Search(query).results
    for i, video in enumerate(search_results):
        print(f"{i + 1}. {video.title}")
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

# Fonction pour jouer l'audio avec ffplay
def play_audio_opus(audio_file, start_time=0):
    global ffplay_process, current_audio_file, playback_start_time
    current_audio_file = audio_file
    
    if ffplay_process:
        ffplay_process.terminate()
        ffplay_process.wait()

    # Enregistrer le temps de démarrage (ajusté pour le début)
    playback_start_time = time.time() - start_time
    ffplay_process = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-hide_banner', '-ss', str(start_time), audio_file])

# Fonction pour basculer Play/Pause
def toggle_play_pause():
    global is_playing, ffplay_process, audio_position, playback_start_time

    if is_playing:
        print("Mise en pause...")
        # Calculer le temps écoulé depuis le début de la lecture
        audio_position = time.time() - playback_start_time
        ffplay_process.terminate()
        ffplay_process = None
        is_playing = False
    else:
        print(f"Reprise à {audio_position:.2f} secondes...")
        play_audio_opus(current_audio_file, audio_position)
        is_playing = True

# Fonction pour surveiller la fin de la lecture
def monitor_playback():
    global ffplay_process, is_playing, current_index, current_playlist

    while True:
        if ffplay_process and ffplay_process.poll() is not None:  # Si la lecture est terminée
            is_playing = False
            next_track()  # Passer à la piste suivante
        time.sleep(1)  # Vérifier toutes les secondes

# Fonction principale de la playlist
# Fonction principale de la playlist
def playlist():
    global root, playpause_button, title_label, is_playing, current_playlist, current_index

    # Créer le dossier Playlists s'il n'existe pas
    if not os.path.exists(playlists_folder):
        os.makedirs(playlists_folder)

    # Créer la fenêtre principale
    root = tk.Tk()
    root.title("Lecteur de Playlists")
    root.config(bg='#404040')
    
    # Récupérer la liste des playlists disponibles
    playlists = [f for f in os.listdir(playlists_folder) if f.endswith('.txt')]
    if not playlists:
        messagebox.showerror("Erreur", "Aucune playlist trouvée dans le dossier 'Playlists'!")
        return

    # Widgets GUI
    def create_gui():
        nonlocal playlists

        # Cadre pour la sélection de playlist
        top_frame = tk.Frame(root, bg='#404040')
        top_frame.pack(pady=10)

        # Menu déroulant pour les playlists
        selected_playlist = tk.StringVar(value=playlists[0])
        playlist_menu = tk.OptionMenu(top_frame, selected_playlist, *playlists)
        playlist_menu.config(bg='#606060', fg='white')
        playlist_menu.pack(side='left', padx=10)

        # Bouton de chargement
        load_button = tk.Button(top_frame, text="Charger", 
                              command=lambda: load_selected_playlist(selected_playlist.get()), 
                              bg='#101010', fg='white')
        load_button.pack(side='left', padx=10)

        # Label pour le titre
        global title_label
        title_label = tk.Label(root, text="", font=("Helvetica", 12), bg='#404040', fg='white')
        title_label.pack(pady=10)

        # Boutons de contrôle
        control_frame = tk.Frame(root, bg='#404040')
        control_frame.pack(pady=10)

        prev_button = tk.Button(control_frame, text="|<<", command=prev_track, bg='#aa2050', fg='white')
        prev_button.pack(side='left', padx=5)

        global playpause_button
        playpause_button = tk.Button(control_frame, text="Play/Pause", command=toggle_play_pause, bg='#802080', fg='white')
        playpause_button.pack(side='left', padx=5)

        next_button = tk.Button(control_frame, text=">>|", command=next_track, bg='#5020aa', fg='white')
        next_button.pack(side='left', padx=5)

    # Fonction pour charger une playlist
    def load_selected_playlist(playlist_name):
        global current_playlist, current_index
        try:
            playlist_path = os.path.join(playlists_folder, playlist_name)
            current_playlist = pd.read_csv(playlist_path, header=None, names=['title'])
            current_index = 0
            play_song(current_index)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de chargement:\n{str(e)}")

    # Fonctions de contrôle de lecture
    def play_song(index):
        global current_index
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
                threading.Thread(target=lambda: play_audio_opus(audio_file), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de lecture:\n{str(e)}")

    def next_track():
        global current_index
        if current_playlist is not None and current_index < len(current_playlist) - 1:
            current_index += 1
            play_song(current_index)

    def prev_track():
        global current_index
        if current_playlist is not None and current_index > 0:
            current_index -= 1
            play_song(current_index)

    # Fonction pour surveiller la fin de la lecture
    def monitor_playback():
        global ffplay_process, is_playing, current_index, current_playlist

        while True:
            if ffplay_process and ffplay_process.poll() is not None:  # Si la lecture est terminée
                is_playing = False
                next_track()  # Passer à la piste suivante
            time.sleep(1)  # Vérifier toutes les secondes

    # Initialisation de l'interface
    create_gui()
    load_selected_playlist(playlists[0])  # Charge la première playlist par défaut

    # Démarrer le thread de surveillance de la lecture
    threading.Thread(target=monitor_playback, daemon=True).start()

    root.mainloop()


# Fonction principale du programme pour la recherche et écoute d'une musique unique
def one_shot():
    global root, playpause_button, title_label, is_playing
    is_playing = False

    query = input("Recherche YouTube (ex: 'Lo-fi music'): ")
    search_results = search_video(query)
    video_choice = int(input("Numéro de la vidéo: ")) - 1
    chosen_video = search_results[video_choice]

    video = YouTube(chosen_video.watch_url)
    audio_file = download_audio(video)

    if audio_file:
        global current_audio_file
        current_audio_file = audio_file
        
        root = tk.Tk()
        root.title("Lecteur Audio")
        root.config(bg='#121212')
        
        title_label = tk.Label(root, text=f"{chosen_video.title}", font=("Helvetica", 14), bg='#121212', fg="white")
        title_label.pack(pady=10)

        playpause_button = tk.Button(root, text="Play/Pause", command=toggle_play_pause, font=("Helvetica", 12), bg="#4CAF50", fg="white")
        playpause_button.pack(pady=10)

        threading.Thread(target=lambda: play_audio_opus(audio_file), daemon=True).start()
        root.mainloop()

# Point d'entrée du programme
if __name__ == "__main__":
    # Choisir entre une recherche unique ou une playlist
    choice = input("Choose option:\n1. One-shot music search\n2. Playlist\n Enter choice (1/2): ")
    if choice == '1':
        one_shot()
    elif choice == '2':
        playlist()