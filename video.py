import os
import pygame
from pytubefix import YouTube
from pytube import Search
from pydub import AudioSegment  # Importation pour la conversion audio

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
def play_audio(audio_file):
    print("Playing audio...")
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()

    # Boucle jusqu'à ce que la musique soit terminée
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# Fonction principale du programme
def main():
    query = input("Enter the YouTube search term (e.g., 'Lo-fi music'): ")
    # Recherche de vidéos sur YouTube
    search_results = search_video(query)
    # Demander à l'utilisateur de choisir une vidéo
    video_choice = int(input("Enter the number of the video to listen to: ")) - 1
    chosen_video = search_results[video_choice]

    # Utiliser l'URL de la vidéo via watch_url
    video = YouTube(chosen_video.watch_url)  # Utilisation de l'URL via watch_url

    # Télécharger l'audio de la vidéo choisie
    print("Downloading audio file...")
    audio_file = download_audio(video)
    if audio_file:
        # Convertir le fichier audio en MP3 si nécessaire et récupérer le taux d'échantillonnage
        mp3_file, sample_rate = convert_audio(audio_file)

        # Afficher l'échantillonnage (taux d'échantillonnage)
        print(f"Audio sample rate: {sample_rate} Hz")

        # Lire le fichier MP3 converti
        play_audio(mp3_file)

        # Supprimer les fichiers audio après lecture
        os.remove(audio_file)
        os.remove(mp3_file)
        print("Audio file deleted.")

if __name__ == "__main__":
    main()
