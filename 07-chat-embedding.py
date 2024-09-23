#!/usr/bin/env python3
# coding: utf-8

"""
Deutsches Skript zur Implementierung eines Chatbots mit Retrieval-Augmented
Generation (RAG)

Dieses Python-Skript ermöglicht die Interaktion mit einem Chatbot, der auf
modernen Sprachmodellen basiert und Informationen aus einer Elasticsearch-
Datenbank abrufen kann. Dabei wird die Frage des Nutzers in einen semantischen
Vektor umgewandelt, um relevante Dokumente aus dem Index zu finden. Anschließend
werden diese Dokumente verwendet, um eine fundierte Antwort zu generieren.

**Hauptfunktionen:**
- Erzeugung von Embeddings der Benutzerfrage mit XLM-Roberta.
- Suche nach relevanten Dokumenten in Elasticsearch basierend auf
  Kosinus-Ähnlichkeit.
- Dynamische Konstruktion des Eingabe-Prompts für das Sprachmodell unter
  Einbeziehung der gefundenen Dokumente.
- Nutzung des Ollama-Clients zur Generierung natürlicher Antworten.
- Unterstützung eines laufenden Gesprächsverlaufs mit Kontext.
- Möglichkeit, Debugging-Informationen mittels des Flags `-v` anzuzeigen.

**Hinweise zur Verwendung:**
- Stellen Sie sicher, dass Elasticsearch läuft und der angegebene Index
  vorhanden ist.
- Setzen Sie die Umgebungsvariablen `ES_USER` und `ES_PASSWORD` für die
  Authentifizierung.
- Das Skript benötigt die Pakete `transformers`, `torch`, `elasticsearch` und
  `ollama`.
"""

import argparse
import getpass
from elasticsearch import Elasticsearch
from transformers import XLMRobertaTokenizer, XLMRobertaModel
import torch
import ollama
import os

# Initialisiert den Ollama-Client
client = ollama.Client()

# Funktion zur Erstellung eines Embeddings für die Frage des Benutzers
def create_embedding_for_question(model, tokenizer, question):
    inputs = tokenizer(
        question,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=512
    )  # XLM-Roberta hat eine maximale Länge von 512 Tokens
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().tolist()

# Funktion zum Bereinigen der Antwort durch Entfernen doppelter Zeilenumbrüche
def clean_response(response):
    return response.replace("\n\n", "\n")

# Funktion zum Bereinigen des Dokuments durch Entfernen doppelter Zeilenumbrüche
def clean_document(document):
    return document.replace("\n\n", "\n")

# Hauptfunktion
def main(index_name, system_prompt, welcome_message, user_prefix,
         bot_prefix, doc_limit, verbose):

    # Vordefinieren des Modells durch Senden einer leeren Anfrage
    print(f"Das Chatten mit llama3.1 wird vorbereitet, unterstützt durch "
          f"den Dokumentenindex '{index_name}' und xlm-roberta-base. "
          "Während die Modelle laden, lesen Sie diese Nachricht.")
    try:
        response = client.generate(model="llama3.1")
    except Exception as e:
        print(f"Fehler beim Laden des Modells: {e}")
        return

    if verbose:
        print("Modelle erfolgreich geladen.")

    # Initialisieren des Gesprächsverlaufs mit dem System-Prompt
    conversation_history = system_prompt + "\n\n"

    # Elasticsearch-Host
    es_host = "http://localhost:9200"

    # Benutzername und Passwort aus Umgebungsvariablen abrufen
    es_user = os.getenv('ES_USER')
    es_password = os.getenv('ES_PASSWORD')

    # Falls Benutzername oder Passwort nicht gesetzt sind, nachfragen
    if not es_user:
        es_user = input(
            "Bitte geben Sie Ihren Elasticsearch-Benutzernamen ein: "
        )
    if not es_password:
        es_password = getpass.getpass(
            "Bitte geben Sie Ihr Elasticsearch-Passwort ein: "
        )

    es = Elasticsearch(
        hosts=[es_host],
        basic_auth=(es_user, es_password),
        request_timeout=30,
        max_retries=10,
        retry_on_timeout=True
    )

    # Laden des XLM-Roberta-Modells und Tokenizers
    tokenizer = XLMRobertaTokenizer.from_pretrained('xlm-roberta-base')
    model = XLMRobertaModel.from_pretrained('xlm-roberta-base')

    if verbose:
        print("XLM-Roberta-Modell und Tokenizer erfolgreich geladen.")

    # Willkommensnachricht ausgeben
    print("\n" + bot_prefix + welcome_message + "\n")
    conversation_history += bot_prefix + welcome_message + "\n\n"

    while True:
        # Benutzerfrage mit user_prefix abfragen
        user_question = input(f"{user_prefix}")
        conversation_history += user_prefix + user_question + "\n\n"

        # Embedding für die Benutzerfrage erstellen
        user_embedding = create_embedding_for_question(
            model, tokenizer, user_question
        )

        if verbose:
            print("Benutzer-Embedding erstellt.")

        # Elasticsearch-Abfrage basierend auf Kosinus-Ähnlichkeit
        search_query = {
            "query": {
                "script_score": {
                    "query": {
                        "match_all": {}
                    },
                    "script": {
                        "source": (
                            "cosineSimilarity(params.query_vector, "
                            "'embedding_vector') + 1.0"
                        ),
                        "params": {
                            "query_vector": user_embedding
                        }
                    }
                }
            },
            "size": doc_limit
        }

        try:
            es_response = es.search(index=index_name, body=search_query)
            if verbose:
                print(f"Elasticsearch-Antwort: {es_response}")
        except Exception as e:
            print(f"Fehler bei der Abfrage von Elasticsearch: {e}")
            continue

        # Dokumente aus der Antwort extrahieren
        documents = []
        if es_response['hits']['hits']:
            for hit in es_response['hits']['hits']:
                content = hit['_source'].get('content', '')
                documents.append(clean_document(content))
            if verbose:
                print(f"{len(documents)} Dokumente gefunden.")
        else:
            print("Keine Dokumente gefunden.")
            continue

        # Prompt für das Modell erstellen (Prompt bleibt auf Englisch)
        prompt = conversation_history
        prompt += "Answer the question based on the following information:\n\n"

        for i, doc in enumerate(documents):
            prompt += f"Document {i+1}:\n{doc}\n\n"

        prompt += f"Here is the question again: {user_question}\n\n"
        prompt += (
            "Answer the question naturally, in the user's language. "
            "If no question is asked, just keep the conversation going."
        )

        if verbose:
            print("Prompt für das Modell erstellt.")

        # Antwort vom Modell generieren
        try:
            response = client.generate(
                prompt=prompt,
                model="llama3.1",
                options={'temperature': 0, 'prompt': ''}
            )
            if verbose:
                print(f"Antwort vom Modell erhalten: {response}")
        except Exception as e:
            print(f"Fehler bei der Generierung der Antwort: {e}")
            continue

        # Bereinigte Antwort des Modells anzeigen
        if response and 'response' in response:
            clean_resp = clean_response(response['response'])
            # Antwort mit bot_prefix ausgeben
            print(f"\n{bot_prefix}{clean_resp}\n")
            conversation_history += bot_prefix + clean_resp + "\n\n"
        else:
            print("Keine gültige Antwort vom Modell erhalten.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Elasticsearch und Ollama RAG Chat Skript"
    )
    parser.add_argument(
        "index_name",
        type=str,
        help="Name des Elasticsearch-Index"
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default="You are a helpful assistant.",
        help="System-Prompt für das Modell."
    )
    parser.add_argument(
        "--welcome-message",
        type=str,
        default="Willkommen beim RAG Chat",
        help="Willkommensnachricht für den Nutzer."
    )
    parser.add_argument(
        "--user-prefix",
        type=str,
        default="Du sagst: ",
        help="Prefix für Benutzereingaben."
    )
    parser.add_argument(
        "--bot-prefix",
        type=str,
        default="Antwort: ",
        help="Prefix für Bot-Antworten."
    )
    parser.add_argument(
        "--doc-limit",
        type=int,
        default=5,
        help="Anzahl der Dokumente im Prompt (Standard: 5)"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Aktiviert Debugging-Informationen.'
    )

    args = parser.parse_args()
    main(
        args.index_name,
        system_prompt=args.system_prompt,
        welcome_message=args.welcome_message,
        user_prefix=args.user_prefix,
        bot_prefix=args.bot_prefix,
        doc_limit=args.doc_limit,
        verbose=args.verbose
    )