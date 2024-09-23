#!/usr/bin/env python3
"""
Dieses Skript dient dazu, Dokumente aus einem Elasticsearch-Index zu lesen,
deren Inhalte zu tokenisieren und in kleinere Chunks aufzuteilen, die dann
in einem neuen Index gespeichert werden. Dies ist besonders nützlich, wenn
Dokumente sehr lang sind und in handlichere Abschnitte zerlegt werden sollen,
beispielsweise für die Verarbeitung mit Sprachmodellen oder für detailliertere
Analysen.

Das Skript verwendet den XLM-Roberta-Tokenizer aus der Transformers-Bibliothek,
um den Text in Tokens zu zerlegen. Anschließend werden die Tokens in Chunks
einer festgelegten maximalen Länge aufgeteilt. Die Chunks werden mit relevanten
Metadaten versehen und in einen neuen Elasticsearch-Index geschrieben.

Verwendung:
    python3 script_name.py index_name [--max_token_length N] [-v]

Parameter:
    index_name: Name des Quell-Index in Elasticsearch.
    --max_token_length: (Optional) Maximale Anzahl von Tokens pro Chunk.
                        Standard ist 512.
    -v, --verbose: (Optional) Aktiviert die Ausgabe von Debugging-Informationen.

Hinweise:
- Das Skript stellt eine Verbindung zu Elasticsearch her und erwartet, dass die
  Umgebungsvariablen ES_USER und ES_PASSWORD gesetzt sind oder diese bei
  der Ausführung abgefragt werden.
- Falls der Zielindex bereits existiert, bietet das Skript an, diesen zu löschen
  und neu zu erstellen.
- Während der Verarbeitung wird ein Fortschrittsbalken angezeigt.
- Bei aktiviertem Verbose-Modus werden zusätzliche Informationen ausgegeben.
"""

from elasticsearch import Elasticsearch, helpers
from transformers import XLMRobertaTokenizer
from transformers import logging as transformers_logging
import argparse
import sys
import getpass
import os
import warnings

# Deaktiviert die Warnungen des Transformers-Moduls
transformers_logging.set_verbosity_error()

# Initialisiert den XLM-Roberta-Tokenizer
tokenizer = XLMRobertaTokenizer.from_pretrained('xlm-roberta-base')


# Funktion zum Tokenisieren des Textes und Aufteilen in Chunks
def tokenize_and_chunk(content, max_token_length=512):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tokens = tokenizer.encode(content, add_special_tokens=False)
        chunks = [tokens[i:i + max_token_length]
                  for i in range(0, len(tokens), max_token_length)]
        text_chunks = [
            tokenizer.decode(chunk, clean_up_tokenization_spaces=True)
            for chunk in chunks
        ]
        return text_chunks


# Funktion zur Anzeige eines Fortschrittsbalkens
def print_progress(processed, total):
    progress = processed / total
    bar_length = 40  # Länge des Fortschrittsbalkens
    block = int(bar_length * progress)
    progress_bar = '=' * block + '.' * (bar_length - block)
    percent = round(progress * 100, 2)
    sys.stdout.write(f"\r[{progress_bar}] {percent}%")
    sys.stdout.flush()


# Funktion zum Erstellen des neuen Indexes
def create_target_index(es, target_index):
    target_mapping = {
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
                "chunk_number": {"type": "integer"},
                "tags": {"type": "keyword"},
                "embedding_vector": {
                    "type": "dense_vector",
                    "dims": 768
                }
            }
        }
    }

    if es.indices.exists(index=target_index):
        response = input(
            f"Der Chunk-Index {target_index} existiert bereits. "
            "Möchten Sie ihn löschen? (ja/nein): "
        ).strip().lower()
        if response == 'ja':
            es.indices.delete(index=target_index)
            es.indices.create(index=target_index, body=target_mapping)
            print(f"Index {target_index} wurde gelöscht und neu erstellt.")
        else:
            print(f"Index {target_index} wurde nicht gelöscht. Abbruch.")
            sys.exit(1)
    else:
        es.indices.create(index=target_index, body=target_mapping)


# Dokumente verarbeiten und in Chunks aufteilen
def process_documents(es, source_index, target_index, max_token_length=512,
                      scroll_time='30m', verbose=False):
    create_target_index(es, target_index)

    try:
        total_docs = es.count(index=source_index)["count"]
        docs = helpers.scan(
            es, index=source_index,
            query={"query": {"match_all": {}}},
            scroll=scroll_time
        )
        actions = []
        processed_count = 0

        for doc in docs:
            processed_count += 1
            content = doc["_source"].get("content", "")

            if not content:
                if verbose:
                    print(f"Dokument {doc['_id']} hat keinen Inhalt "
                          "und wird übersprungen.")
                continue

            # Tokenisiere und erstelle Chunks
            chunks = tokenize_and_chunk(content, max_token_length)
            if verbose:
                print(f"Dokument {doc['_id']} wurde in {len(chunks)} "
                      "Chunks aufgeteilt.")

            for i, chunk in enumerate(chunks):
                new_doc = {
                    "_index": target_index,
                    "_source": {
                        "content": chunk,
                        "content_length": len(chunk),
                        "content_type": doc["_source"].get("content_type"),
                        "author": doc["_source"].get("author"),
                        "date": doc["_source"].get("date"),
                        "keywords": doc["_source"].get("keywords"),
                        "language": doc["_source"].get("language"),
                        "title": doc["_source"].get("title"),
                        "file_name": doc["_source"].get("file_name"),
                        "path": doc["_source"].get("path"),
                        "tags": doc["_source"].get("tags"),
                        "chunk_number": i + 1
                    }
                }
                actions.append(new_doc)

            # Fortschritt anzeigen
            print_progress(processed_count, total_docs)

            if len(actions) >= 1000:
                try:
                    helpers.bulk(es, actions)
                    if verbose:
                        print(f"{len(actions)} Dokumente wurden in den Index "
                              f"{target_index} geschrieben.")
                    actions = []
                except Exception as e:
                    print(f"Fehler beim Schreiben von Dokumenten in den Index: {e}")
                    sys.exit(1)

        if actions:
            try:
                helpers.bulk(es, actions)
                if verbose:
                    print(f"{len(actions)} verbleibende Dokumente wurden in "
                          f"den Index {target_index} geschrieben.")
            except Exception as e:
                print(f"Fehler beim Schreiben von Dokumenten in den Index: {e}")
                sys.exit(1)

    except Exception as e:
        print(f"Ein Fehler ist beim Verarbeiten der Dokumente aufgetreten: {e}")
        sys.exit(1)


# Skript ausführen
if __name__ == "__main__":
    # Argumente einlesen
    parser = argparse.ArgumentParser(
        description='Verarbeitet Elasticsearch-Dokumente und teilt sie in Chunks auf.'
    )
    parser.add_argument('index', help='Name des Quell-Index in Elasticsearch.')
    parser.add_argument(
        '--max_token_length', type=int, default=512,
        help='Maximale Größe jedes Chunks in Tokens. Standard ist 512.'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Aktiviert die Ausgabe von Debugging-Informationen.'
    )

    args = parser.parse_args()

    # Elasticsearch-Host
    es_host = "http://localhost:9200"

    # Benutzername und Passwort aus Umgebungsvariablen holen
    es_user = os.getenv('ES_USER')
    es_password = os.getenv('ES_PASSWORD')

    if not es_user:
        es_user = input("Bitte geben Sie Ihren Elasticsearch-Benutzernamen ein: ")
    if not es_password:
        es_password = getpass.getpass("Bitte geben Sie Ihr Elasticsearch-Passwort ein: ")

    # Verbindung zu Elasticsearch herstellen
    try:
        es = Elasticsearch(
            hosts=[es_host],
            basic_auth=(es_user, es_password),
            request_timeout=30,
            max_retries=10,
            retry_on_timeout=True
        )
    except Exception as e:
        print(f"Fehler beim Verbinden mit Elasticsearch: {e}")
        sys.exit(1)

    # Zielindex als <index>-chunks festlegen
    chunk_index = f"{args.index}-chunks"

    # Prüfen, ob der Quellindex existiert
    if not es.indices.exists(index=args.index):
        print(f"Der Index {args.index} existiert nicht.")
        sys.exit(1)
    else:
        print(f"Verbunden mit dem Index {args.index}.")

    # Dokumente verarbeiten
    process_documents(
        es, args.index, chunk_index,
        args.max_token_length, verbose=args.verbose
    )