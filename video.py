import os
import pygame
import pandas as pd
from pytubefix import YouTube
from pytube import Search
from pydub import AudioSegment
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

# Initialisation de pygame pour la lecture audio
pygame.mixer.init()

# Fonction de recherche d'une vidéo YouTube
def search_video(query):
    print("Searching for videos for:", query)
    search_results = Search(query).results
    for i, video in enumerate(search_results):
        print(f"{i + 1}. {video.title}")
    return search_results

# Fonction pour télécharger l'audio d'une vidéo YouTube
def download_audio(video):
    print("Downloading audio...")
    streams = video.streams.filter(only_audio=True, file_extension='mp4')  # Prise en charge du format MP4 pour l'audio
    if streams:
        stream = streams.first()
        audio_file = stream.download(output_path="Downloads", filename=f"{video.title}.mp4")
        return audio_file
    else:
        print("No audio streams available.")
        return None

# Fonction pour convertir le fichier audio en MP3 avec pydub
def convert_audio(audio_file):
    print("Converting audio to MP3...")
    audio = AudioSegment.from_file(audio_file)  # Charger le fichier audio
    mp3_file = audio_file.replace(".mp4", ".mp3")  # Renommer le fichier en .mp3
    audio.export(mp3_file, format="mp3")  # Exporter en MP3
    return mp3_file, audio.frame_rate  # Retourner le fichier MP3 et le taux d'échantillonnage

# Fonction pour jouer l'audio avec pygame
def play_audio(mp3_file):
    print("Playing audio...")
    pygame.mixer.music.load(mp3_file)
    pygame.mixer.music.play()

# Fonction pour la gestion de la lecture dans l'interface graphique
def toggle_play_pause():
    global is_playing
    if is_playing:
        # Mettre en pause la musique
        pygame.mixer.music.pause()
        playpause_button.config(text="Play")
        is_playing = False
    else:
        # Reprendre la lecture de la musique
        pygame.mixer.music.unpause()
        playpause_button.config(text="Pause")
        is_playing = True

# Fonction pour déplacer la lecture audio avec le curseur
def on_slider_change(val):
    position = float(val)
    pygame.mixer.music.set_pos(position)

# Fonction principale du programme pour la recherche et écoute d'une musique unique
def one_shot():
    global root, playpause_button, slider, title_label, is_playing
    is_playing = False  # Etat initial de la lecture (pas de lecture en cours)

    query = input("Enter the YouTube search term (e.g., 'Lo-fi music'): ")
    # Recherche de vidéos sur YouTube
    search_results = search_video(query)
    # Demander à l'utilisateur de choisir une vidéo
    video_choice = int(input("Enter the number of the video to listen to: ")) - 1
    chosen_video = search_results[video_choice]

    # Utiliser l'URL de la vidéo via watch_url
    video = YouTube(chosen_video.watch_url)

    # Télécharger l'audio de la vidéo choisie
    print("Downloading audio file...")
    audio_file = download_audio(video)
    if audio_file:
        # Convertir le fichier audio en MP3 si nécessaire et récupérer le taux d'échantillonnage
        mp3_file, sample_rate = convert_audio(audio_file)

        # Afficher l'échantillonnage (taux d'échantillonnage)
        print(f"Audio sample rate: {sample_rate} Hz")

        # Initialiser la fenêtre Tkinter
        root = tk.Tk()
        root.title("Audio Player")
        root.config(bg='#121212')  # Fond sombre de l'application
        
        play_audio(mp3_file)
        # Titre de la chanson
        title_label = tk.Label(root, text=f"{chosen_video.title}", font=("Helvetica", 14, "bold"), bg='#121212', fg="#ffffff")
        title_label.pack(pady=10)

        # Bouton Play/Pause
        playpause_button = tk.Button(root, text="Play/Pause", command=toggle_play_pause, font=("Helvetica", 12, "bold"), 
                                     bg="#e76f51", fg="white", activebackground="#ff6f61", relief="flat")
        playpause_button.pack(pady=10)

        # Curseur pour la position de lecture
        slider = tk.Scale(root, from_=0, to=pygame.mixer.Sound(mp3_file).get_length(), orient="horizontal", resolution=1, command=on_slider_change, bg="#121212", fg="white", sliderlength=20)
        slider.pack(pady=10)

        # Mettre à jour le curseur pendant la lecture
        while pygame.mixer.music.get_busy():  # Tant que la musique joue
            root.update()  # Met à jour l'interface graphique

        # Supprimer les fichiers audio après lecture
        os.remove(audio_file)
        os.remove(mp3_file)
        print("Audio file deleted.")

        # Démarrer l'interface graphique
        root.mainloop()

# Fonction principale de la playlist
def playlist():
    global root, playpause_button, slider, title_label, is_playing
    is_playing = False  # Etat initial de la lecture (pas de lecture en cours)

    # Sélectionner le fichier CSV contenant la playlist
    playlist_path = filedialog.askopenfilename()
    playlist = pd.read_csv(playlist_path, header=None, names=['title'])
    print(playlist)
    
    # Créer une fenêtre Tkinter pour la lecture audio
    root = tk.Tk()
    root.title("Audio Player")
    root.config(bg='#121212')  # Fond sombre de l'application
    
    # Initialiser le label de titre et autres éléments de l'interface graphique
    title_label = tk.Label(root, text="", font=("Helvetica", 14, "bold"), bg='#121212', fg="#ffffff")
    title_label.pack(pady=10)

    # Frame pour les boutons (Play/Pause, Previous, Next)
    button_frame = tk.Frame(root, bg='#121212')  # Créer une frame pour les boutons
    button_frame.pack(pady=10)

    # Fonction pour aller à la piste suivante
    def next_track():
        nonlocal current_index
        if current_index < len(playlist) - 1:
            current_index += 1
            play_song(current_index)

    # Fonction pour aller à la piste précédente
    def prev_track():
        nonlocal current_index
        if current_index > 0:
            current_index -= 1
            play_song(current_index)

    # Bouton Previous
    prev_button = tk.Button(button_frame, text="|<<", command=prev_track, font=("Helvetica", 12, "bold"), 
                            bg="#cc2080", fg="white", relief="flat")
    prev_button.pack(side="left", padx=10)  # Pack à gauche dans la frame avec un espacement
    
    # Bouton Play/Pause
    playpause_button = tk.Button(button_frame, text="Play/Pause", command=toggle_play_pause, font=("Helvetica", 12, "bold"), 
                                 bg="#aa20aa", fg="white", activebackground="#ff6f61", relief="raised")
    playpause_button.pack(side="left", padx=10)  # Pack à gauche dans la frame avec un espacement

    # Bouton Next
    next_button = tk.Button(button_frame, text=">>|", command=next_track, font=("Helvetica", 12, "bold"), 
                            bg="#8020cc", fg="white", relief="flat")
    next_button.pack(side="left", padx=10)  # Pack à gauche dans la frame avec un espacement

    # Initialiser l'index de la chanson actuelle
    current_index = 0

    # Fonction pour jouer une chanson donnée par son index dans la playlist
    def play_song(index):
        global current_index
        song_title = playlist['title'][index]
        print(f"Playing: {song_title}")
        
        query = song_title  # Titre de la chanson
        search_results = search_video(query)  # Recherche de vidéos YouTube
        video_choice = int(1) - 1  # Choisir la première vidéo (tu peux changer la logique ici si nécessaire)
        chosen_video = search_results[video_choice]

        # Utiliser l'URL de la vidéo via watch_url
        video = YouTube(chosen_video.watch_url)

        # Télécharger l'audio de la vidéo choisie
        print("Downloading audio file...")
        audio_file = download_audio(video)
        if audio_file:
            # Convertir le fichier audio en MP3 si nécessaire et récupérer le taux d'échantillonnage
            mp3_file, sample_rate = convert_audio(audio_file)

            # Afficher l'échantillonnage (taux d'échantillonnage)
            print(f"Audio sample rate: {sample_rate} Hz")

            # Jouer l'audio
            play_audio(mp3_file)

            # Mettre à jour le titre de la chanson
            title_label.config(text=f"{chosen_video.title}")  # Mettre à jour le titre de la chanson

            # Mettre à jour le curseur pendant la lecture
            while pygame.mixer.music.get_busy():  # Tant que la musique joue
                root.update()  # Met à jour l'interface graphique
    
    # Commencer avec la première chanson
    play_song(current_index)

    # La fenêtre restera ouverte, sauf si l'utilisateur la ferme explicitement
    root.mainloop()

if __name__ == "__main__":
    # Choisir entre une recherche unique ou une playlist
    choice = input("Choose option:\n1. One-shot music search\n2. Playlist\nEnter choice (1/2): ")
    if choice == '1':
        one_shot()
    elif choice == '2':
        playlist()
