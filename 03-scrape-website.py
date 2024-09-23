#!/usr/bin/env python3
# coding: utf-8

"""
Dieses Skript ist ein einfacher Web-Crawler, der eine angegebene Domain durchsucht
und alle darin enthaltenen HTML-Seiten und Dateien (wie PDF-Dateien) herunterlädt.
Es startet von einer Start-URL und folgt Links innerhalb der Domain und des
angegebenen Unterverzeichnisses. Das Skript speichert die heruntergeladenen Dateien
in einer strukturierten Ordnerhierarchie, die der Struktur der Website entspricht.

Funktionen:
- Herunterladen von HTML-Seiten und PDF-Dateien von einer bestimmten Domain.
- Speichern der Dateien in einem lokalen Verzeichnis mit entsprechender Ordnerstruktur.
- Begrenzung der maximal herunterzuladenden Dateien, um die Ausführung zu kontrollieren.
- Fehlerbehandlung mit aussagekräftigen Fehlermeldungen.
- Optionales Debugging mittels eines "verbose"-Modus, der zusätzliche Informationen
  während der Ausführung ausgibt.

Verwendung:
Das Skript wird über die Kommandozeile aufgerufen und akzeptiert verschiedene
Argumente zur Anpassung des Verhaltens:
- Angabe der Start-URL der Domain.
- Festlegung des Zielverzeichnisses zum Speichern der Dateien.
- Begrenzung der maximalen Anzahl herunterzuladender Dateien.
- Aktivierung des "verbose"-Modus für detaillierte Ausgaben.
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import argparse

# Funktion zum Herunterladen und Speichern einer Datei oder HTML-Seite
def download_file(url, folder, verbose=False):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Überprüfe den Content-Type
        content_type = response.headers.get('Content-Type', '').lower()
        if not content_type:
            raise ValueError("Konnte den Content-Type nicht bestimmen.")

        # Nur bestimmte Dateien speichern
        if not any(ct in content_type for ct in ['text', 'html', 'pdf']):
            if verbose:
                print(f"Datei übersprungen (Content-Type: {content_type}): {url}")
            return False

        # Bestimme die Dateiendung basierend auf dem Content-Type
        if 'text/html' in content_type:
            extension = ".html"
        elif 'application/pdf' in content_type:
            extension = ".pdf"
        else:
            extension = os.path.splitext(urlparse(url).path)[1]

        # Bestimme den lokalen Dateinamen und den Verzeichnispfad
        parsed_url = urlparse(url)
        path_parts = [
            unquote(part) for part in parsed_url.path.strip("/").split("/")
        ]
        if not path_parts or path_parts == ['']:
            path_parts = ["index"]

        local_filename = path_parts[-1] if path_parts[-1] else "index"
        if not local_filename.endswith(extension):
            local_filename += extension

        # Erstelle den Verzeichnispfad
        local_folder = os.path.join(folder, *path_parts[:-1])
        os.makedirs(local_folder, exist_ok=True)

        local_file_path = os.path.join(local_folder, local_filename)

        # Überprüfen, ob die Datei bereits existiert
        if os.path.exists(local_file_path):
            if verbose:
                print(f"Datei existiert bereits und wird übersprungen: {local_file_path}")
            return False

        # Datei speichern
        with open(local_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Heruntergeladen: {url} als {local_file_path}")
        return True  # Erfolgreich heruntergeladen
    except Exception as e:
        print(f"Fehler beim Herunterladen der Datei {url}: {e}")
        return False  # Fehlgeschlagen

# Funktion zum Abrufen aller Dateien von einer Seite
def crawl_and_download(start_url, folder, max_files, verbose=False):
    visited_urls = set()
    urls_to_visit = [start_url]
    files_downloaded = 0

    base_url = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
    base_path = urlparse(start_url).path.rstrip('/')

    while urls_to_visit and files_downloaded < max_files:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)

        try:
            response = requests.get(current_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # HTML-Seite speichern
            if download_file(current_url, folder, verbose):
                files_downloaded += 1
                if files_downloaded >= max_files:
                    break

            # Durchsuche alle Links auf der aktuellen Seite
            for link in soup.find_all('a', href=True):
                href = link['href']
                file_url = urljoin(current_url, href)
                file_extension = os.path.splitext(
                    urlparse(file_url).path
                )[1].lower()
                parsed_file_url = urlparse(file_url)

                # Nur innerhalb der Domain und des Pfades fortfahren
                if (parsed_file_url.netloc == urlparse(start_url).netloc and
                    parsed_file_url.path.startswith(base_path)):

                    # PDF-Dateien herunterladen
                    if file_extension == '.pdf':
                        if download_file(file_url, folder, verbose):
                            files_downloaded += 1
                            if files_downloaded >= max_files:
                                break

                    # HTML-Dateien zur Besuchsliste hinzufügen
                    elif (file_extension in ['.html', '.htm'] or not file_extension):
                        if (file_url not in visited_urls and
                            file_url not in urls_to_visit):
                            urls_to_visit.append(file_url)
                elif file_extension == '.pdf':
                    # PDFs von außerhalb der Domain herunterladen
                    if download_file(file_url, folder, verbose):
                        files_downloaded += 1
                        if files_downloaded >= max_files:
                            break

        except Exception as e:
            print(f"Fehler beim Abrufen von {current_url}: {e}")

    print(f"{files_downloaded} Dateien erfolgreich heruntergeladen.")

# Hauptfunktion
def main():
    parser = argparse.ArgumentParser(
        description="Crawlt eine Domain und lädt Dateien und HTML-Seiten herunter."
    )
    parser.add_argument(
        "domain",
        help="Die Startseite der Domain (z.B. https://example.com)"
    )
    parser.add_argument(
        "-d", "--directory",
        help=("Das Verzeichnis, in dem die Dateien gespeichert werden "
              "(Standard: Ordner mit Domainnamen)"),
        default=None
    )
    parser.add_argument(
        "-m", "--max_files",
        help=("Maximale Anzahl der herunterzuladenden Dateien (Standard: 100)"),
        type=int,
        default=100
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Aktiviere detaillierte Ausgaben",
        action="store_true"
    )

    args = parser.parse_args()

    # Setze das Zielverzeichnis
    if args.directory:
        target_folder = args.directory
    else:
        target_folder = os.path.join(
            os.getcwd(), urlparse(args.domain).netloc
        )

    # Erstelle das Verzeichnis, falls es nicht existiert
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # Starte den Crawler
    try:
        crawl_and_download(
            args.domain, target_folder, args.max_files, args.verbose
        )
    except Exception as e:
        print(f"Fehler bei der Ausführung: {e}")

if __name__ == "__main__":
    main()