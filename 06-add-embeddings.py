#!/usr/bin/env python3
# coding: utf-8

"""
Beschreibung:
Dieses Skript generiert Embedding-Vektoren für alle Dokumente in einem angegebenen
Elasticsearch-Index und speichert diese Vektoren im jeweiligen Dokument unter dem Feld
'embedding_vector'. Es verwendet das vortrainierte Modell 'xlm-roberta-base' von Hugging Face,
um Texte zu repräsentieren.

Anwendung:
- Das Skript verbindet sich mit einem Elasticsearch-Cluster und verarbeitet alle Dokumente im
  angegebenen Index.
- Es extrahiert den Inhalt aus dem Feld 'content' jedes Dokuments.
- Es erstellt Embeddings für den Textinhalt mit Hilfe des XLM-Roberta-Modells.
- Die generierten Embedding-Vektoren werden dem Dokument hinzugefügt und zurück in den Index
  gespeichert.

Voraussetzungen:
- Installierte Python-Pakete: elasticsearch, transformers, torch
- Zugriff auf einen laufenden Elasticsearch-Cluster
- Das Skript erwartet, dass die Umgebungsvariablen 'ES_USER' und 'ES_PASSWORD' gesetzt sind
  oder fordert den Benutzer zur Eingabe auf.

Weitere Hinweise:
- Dieses Skript demonstriert den Einsatz von NLP-Modellen zur Textrepräsentation und die
  Integration mit Elasticsearch zur Speicherung und Abfrage von Daten.
- Es zeigt, wie man mit großen Datenmengen in Elasticsearch umgeht und effiziente
  Verarbeitungstechniken wie die Scroll-API verwendet.
- Der Code beinhaltet auch eine Fortschrittsanzeige und Fehlerbehandlung, um den
  Verarbeitungsstatus zu überwachen.

Verwendung:
- Führen Sie das Skript mit dem Indexnamen als Argument aus:
  `python3 scriptname.py indexname`
- Verwenden Sie das Flag `-v` oder `--verbose`, um detaillierte Debugging-Informationen zu
  erhalten:
  `python3 scriptname.py indexname --verbose`
"""

import sys
import argparse
import getpass
import os
from elasticsearch import Elasticsearch
from transformers import XLMRobertaTokenizer, XLMRobertaModel
import torch

# Funktion, um Embeddings für alle Dokumente im Index zu generieren
def process_documents(es, index, verbose=False):
    # XLM-Roberta Modell und Tokenizer laden
    tokenizer = XLMRobertaTokenizer.from_pretrained('xlm-roberta-base')
    model = XLMRobertaModel.from_pretrained('xlm-roberta-base')

    if verbose:
        print("Modell und Tokenizer erfolgreich geladen.")

    # Anzahl der Dokumente im Index abrufen
    try:
        total_docs = es.count(index=index)['count']
    except Exception as e:
        print("Fehler beim Abrufen der Dokumentanzahl:")
        print(str(e))
        sys.exit(1)

    print(f"Verarbeite {total_docs} Dokumente und erstelle Embedding-Vektoren...")

    # Scroll-API verwenden, um alle Dokumente des Index abzurufen
    scroll_size = 1000  # Anzahl der Dokumente pro Abfrage
    scroll_time = '60m'  # Wie lange der Scroll-Zustand aktiv bleibt

    try:
        results = es.search(
            index=index,
            body={"query": {"match_all": {}}, "size": scroll_size},
            scroll=scroll_time
        )
    except Exception as e:
        print("Fehler bei der Suche in Elasticsearch:")
        print(str(e))
        sys.exit(1)

    scroll_id = results['_scroll_id']
    documents = results['hits']['hits']
    processed_docs = 0

    if verbose:
        print(f"Initiale Suche abgeschlossen. Scroll-ID: {scroll_id}")

    def print_progress(processed, total):
        progress = processed / total
        bar_length = 40  # Länge der Fortschrittsanzeige
        block = int(bar_length * progress)
        progress_bar = '=' * block + '.' * (bar_length - block)
        percent = round(progress * 100, 2)
        sys.stdout.write(f"\r[{progress_bar}] {percent}%")
        sys.stdout.flush()

    while len(documents) > 0:
        for doc in documents:
            if verbose:
                print(f"\nVerarbeite Dokument ID: {doc['_id']}")

            # Den Content des Dokuments abrufen
            if 'content' in doc['_source']:
                text = doc['_source']['content']

                # Text tokenisieren und Embeddings erstellen
                inputs = tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    padding="max_length",
                    max_length=512
                )
                with torch.no_grad():
                    outputs = model(**inputs)

                # Mittelwert der Token-Embeddings als finales Text-Embedding verwenden
                embedding_vector = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()

                # Embedding zum Dokument hinzufügen
                doc['_source']['embedding_vector'] = embedding_vector

                # Aktualisiere das Dokument im Index
                try:
                    es.index(index=index, id=doc['_id'], body=doc['_source'])
                except Exception as e:
                    print(f"\nFehler beim Aktualisieren des Dokuments ID {doc['_id']}:")
                    print(str(e))
            else:
                if verbose:
                    print(f"Dokument ID {doc['_id']} hat kein 'content'-Feld.")

            # Dokumente zählen und Fortschritt anzeigen
            processed_docs += 1
            print_progress(processed_docs, total_docs)

        # Weitere Dokumente scannen
        try:
            results = es.scroll(scroll_id=scroll_id, scroll=scroll_time)
        except Exception as e:
            print("\nFehler beim Abrufen weiterer Dokumente mit Scroll:")
            print(str(e))
            sys.exit(1)

        scroll_id = results['_scroll_id']
        documents = results['hits']['hits']

    print("\nAlle Dokumente erfolgreich verarbeitet.")

# Skript ausführen
if __name__ == "__main__":
    # Argumente einlesen
    parser = argparse.ArgumentParser(
        description='Generiere und speichere Embedding-Vektoren für alle Dokumente in einem Elasticsearch-Index.'
    )
    parser.add_argument('index', help='Name des Elasticsearch-Index.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Aktiviere ausführliche Ausgabe.')
    args = parser.parse_args()

    # Elasticsearch host
    es_host = "http://localhost:9200"

    # Benutzername und Passwort aus Umgebungsvariablen abrufen
    es_user = os.getenv('ES_USER')
    es_password = os.getenv('ES_PASSWORD')

    # Prüfen, ob Benutzername oder Passwort nicht gesetzt sind
    if not es_user:
        es_user = input("Geben Sie Ihren Elasticsearch-Benutzernamen ein: ")
    if not es_password:
        es_password = getpass.getpass("Geben Sie Ihr Elasticsearch-Passwort ein: ")

    # Verbindung zu Elasticsearch herstellen
    try:
        es = Elasticsearch(
            hosts=[es_host],
            basic_auth=(es_user, es_password),
            request_timeout=30,  # Zeitlimit für die Anfrage auf 30 Sekunden setzen
            max_retries=10,
            retry_on_timeout=True
        )
    except Exception as e:
        print("Fehler beim Verbinden mit Elasticsearch:")
        print(str(e))
        sys.exit(1)

    # Prüfen, ob der Index existiert
    try:
        if not es.indices.exists(index=args.index):
            print(f"Index {args.index} existiert nicht.")
            sys.exit(1)
        else:
            print(f"Verbunden mit Index {args.index}.")
    except Exception as e:
        print("Fehler beim Überprüfen des Index:")
        print(str(e))
        sys.exit(1)

    # Dokumente verarbeiten
    process_documents(es, args.index, verbose=args.verbose)