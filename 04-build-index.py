#!/usr/bin/env python3
# coding: utf-8

"""
Dieses Skript dient zum Indizieren von Dokumenten aus einem angegebenen
Verzeichnis in einen Elasticsearch-Index. Es verwendet Apache Tika, um
den Inhalt und die Metadaten der Dateien zu extrahieren, und speichert
diese Informationen in Elasticsearch. Das Skript ermöglicht es, einen
neuen Index zu erstellen oder einen bestehenden Index zu ersetzen. Es
durchsucht rekursiv das angegebene Verzeichnis und indiziert alle
gefundenen Dateien. Die Benutzerinteraktion erfolgt auf Deutsch, und
es wird ein optionales Flag `-v` oder `--verbose` bereitgestellt, um
ausführliche Debugging-Informationen anzuzeigen. Das Skript richtet
sich an Informatikschüler und Lehrkräfte, die sich mit der Verarbeitung
von Textdaten und Suchtechnologien beschäftigen. Es demonstriert den
Einsatz von Elasticsearch und Apache Tika zur Indexierung und Suche in
Dokumentensammlungen.
"""

import os
import sys
import argparse
import webbrowser
from elasticsearch import Elasticsearch
from tika import parser as tika_parser
from getpass import getpass

# Funktion zum Erstellen eines Elasticsearch-Clients mit optionaler Authentifizierung
def create_es_client(hosts, username=None, password=None):
    if username and password:
        es = Elasticsearch(hosts=hosts, basic_auth=(username, password))
    else:
        es = Elasticsearch(hosts=hosts)
    # Verbindung testen
    try:
        if not es.ping():
            print("Verbindung zu Elasticsearch fehlgeschlagen.")
            sys.exit(1)
    except Exception as e:
        print(f"Fehler bei der Verbindung zu Elasticsearch: {e}")
        sys.exit(1)
    return es

# Funktion zum Erstellen eines neuen Index oder zum Löschen eines bestehenden
def create_or_replace_index(es, index_name):
    # Überprüfen, ob der Index bereits existiert
    if es.indices.exists(index=index_name):
        # Benutzer fragen, ob der bestehende Index gelöscht werden soll
        response = input(f"Index '{index_name}' existiert bereits. "
                         f"Soll er gelöscht werden (ja/nein)? ").strip().lower()
        if response == 'ja':
            es.indices.delete(index=index_name)
            print(f"Index '{index_name}' wurde gelöscht.")
        else:
            print("Vorgang abgebrochen. Bestehender Index wird nicht geändert.")
            sys.exit(0)  # Skript beenden, da der bestehende Index nicht geändert werden soll

    # Mapping definieren
    index_mapping = {
        "mappings": {
            "properties": {
                "file_name": {"type": "keyword"},
                "content": {"type": "text"},
                "content_length": {"type": "long"},
                "directory_path": {"type": "keyword"},
                "title": {"type": "text"},
                "author": {"type": "text"},
                "keywords": {"type": "text"},
                "content_type": {"type": "keyword"},
                "language": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "embedding_vector": {
                    "type": "dense_vector",
                    "dims": 768  # Größe des Vektors, erstellt von Longformer
                }
            }
        }
    }

    # Index erstellen
    es.indices.create(index=index_name, body=index_mapping)
    print(f"Index '{index_name}' wurde erstellt.")

# Allgemeine Funktion zum Indizieren eines Dokuments mit Tika
def index_doc(es, file_path, index_name, verbose=False):
    # Tika verwenden, um das Dokument zu parsen und Inhalt sowie Metadaten zu extrahieren
    try:
        parsed = tika_parser.from_file(file_path)
    except Exception as e:
        print(f"Fehler beim Parsen der Datei {file_path}: {e}")
        return

    content = parsed.get("content")
    if content is None:
        if verbose:
            print(f"Überspringe Datei {file_path} aufgrund fehlenden Inhalts.")
        return
    content = content.strip()
    content_length = len(content)
    metadata = parsed.get("metadata", {})
    directory_path = os.path.dirname(file_path)

    # Dokumentstruktur, die indiziert werden soll
    doc = {
        "file_name": os.path.basename(file_path),
        "content": content,
        "content_length": content_length,
        "directory_path": directory_path,
        "title": metadata.get("title", ""),
        "author": metadata.get("Author", ""),
        "keywords": metadata.get("Keywords", ""),
        "content_type": metadata.get("Content-Type", ""),
        "language": metadata.get("language", "")
    }

    # Dokument direkt indizieren, ohne Pipeline
    try:
        es.index(index=index_name, document=doc)
        if verbose:
            print(f"Dokument {file_path} erfolgreich indiziert.")
    except Exception as e:
        print(f"Fehler beim Indizieren des Dokuments {file_path}: {e}")

# Funktion zum Indizieren aller Dateien in einem Verzeichnis
def index_files_in_directory(es, directory, index_name, verbose=False):
    processed_files_count = 0  # Zähler für verarbeitete Dateien
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if verbose:
                print(f"Indiziere: {file_path}")
            try:
                index_doc(es, file_path, index_name, verbose)
                processed_files_count += 1  # Zähler erhöhen
            except Exception as e:
                print(f"Fehler beim Indizieren der Datei {file_path}: {e}")
    return processed_files_count  # Gesamtzahl der verarbeiteten Dateien zurückgeben

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description='Indexiere Dokumente in Elasticsearch.')
    arg_parser.add_argument('directory', help='Das Verzeichnis mit den zu indizierenden Dokumenten.')
    arg_parser.add_argument('index_name', nargs='?', help='Name des Elasticsearch-Index. '
                            'Wenn nicht angegeben, wird der Verzeichnisname verwendet.')
    arg_parser.add_argument('-v', '--verbose', action='store_true',
                            help='Aktiviere ausführliche Ausgabe für Debugging.')
    args = arg_parser.parse_args()

    # Verzeichnis und Indexname aus den Argumenten erhalten
    doc_directory = args.directory
    index_name = args.index_name if args.index_name else os.path.basename(
        os.path.abspath(doc_directory))
    verbose = args.verbose

    # Elasticsearch-Host
    es_host = "http://localhost:9200"

    # Benutzername und Passwort aus Umgebungsvariablen erhalten
    es_user = os.getenv('ES_USER')
    es_password = os.getenv('ES_PASSWORD')

    # Überprüfen, ob Benutzername oder Passwort nicht in Umgebungsvariablen gesetzt sind
    if not es_user:
        es_user = input("Bitte Elasticsearch-Benutzernamen eingeben: ")
    if not es_password:
        es_password = getpass("Bitte Elasticsearch-Passwort eingeben: ")

    # Elasticsearch-Client erstellen
    try:
        es = create_es_client(hosts=[es_host], username=es_user, password=es_password)
    except Exception as e:
        print(f"Fehler beim Erstellen des Elasticsearch-Clients: {e}")
        sys.exit(1)

    # Index erstellen oder ersetzen
    try:
        create_or_replace_index(es, index_name)
    except Exception as e:
        print(f"Fehler beim Erstellen oder Ersetzen des Index '{index_name}': {e}")
        sys.exit(1)

    # Indexierungsfunktion ausführen und Anzahl der verarbeiteten Dateien erhalten
    try:
        processed_files_count = index_files_in_directory(
            es, doc_directory, index_name, verbose)
    except Exception as e:
        print(f"Fehler beim Indizieren der Dateien: {e}")
        sys.exit(1)

    # Nachricht über die Erstellung des Index ausgeben
    print(f"Index '{index_name}' wurde erstellt. Insgesamt verarbeitete Dateien: "
          f"{processed_files_count}")

    # Kibana Index Management Seite im Standard-Webbrowser öffnen
    url = "http://localhost:5601/app/management/data/index_management/indices"
    webbrowser.open(url)