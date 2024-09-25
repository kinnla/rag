#!/usr/bin/env python3
# coding: utf-8

"""
Dieses Skript ermöglicht es Ihnen, mit einem lokal geladenen Sprachmodell zu chatten.
Sie können das gewünschte Modell und die Temperatur über die Kommandozeile angeben.
Das Skript lädt das Modell vor und speichert die Chat-Historie, um den
Kontext zu bewahren. Während der Ausführung können Sie Nachrichten eingeben, auf die
das Modell reagieren wird. Um das Programm zu beenden, geben Sie 'exit' ein.

Verwendung:
./simple-chat.py --model <Modellname> --temperature <Wert> [-v]

Parameter:
--model: Das zu verwendende Sprachmodell (Standard: llama3.1)
--temperature: Die Temperatur für die Modellantworten (Standard: 0.8)
-v, --verbose: Aktiviert den Debug-Modus, um zusätzliche Informationen anzuzeigen.

Beispiel:
./simple-chat.py --model llama3.1 --temperature 0.8 -v
"""

import argparse
import sys
import os
from openai import OpenAI

client = OpenAI(
    api_key="8cdef4d5e72f09bd2b4b318ed54ff32",
    base_url = "https://chat-ai.academiccloud.de/v1"
)

# Kommandozeilenargumente für Modell und Temperatur parsen
parser = argparse.ArgumentParser(
    description="Einfacher Chat mit einem lokalen Sprachmodell")
parser.add_argument("--model", type=str, default="meta-llama-3.1-8b-instruct",
                    help="Das zu verwendende Sprachmodell (Standard: meta-llama-3.1-8b-instruct)")
parser.add_argument("--temperature", type=float, default=0.8,
                    help="Die Temperatur für die Modellantworten (Standard: 0.8)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Aktiviere den Debug-Modus")
args = parser.parse_args()

def runQuery(model, prompt="Test", options={}):
    result = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
    ) 
    return result.choices[0].message.content

# Modell vorladen durch Senden einer leeren Anfrage
print(f"Sie werden gleich mit {args.model} chatten.")
print("Bitte warten Sie, während das Modell geladen wird...")

try:
    response = runQuery(model=args.model)
except Exception as e:
    print(f"Fehler beim Laden des Modells: {e}")
    sys.exit(1)

# Konversationshistorie initialisieren
conversation_history = "Assistant: Hallo, wie kann ich Ihnen helfen?\n\n"

# Begrüßung ausgeben
print(f"\n{args.model}: Hallo, wie kann ich Ihnen helfen?\n")

# Chat-Schleife
while True:
    try:
        user_query = input("Sie sagen: ")
    except KeyboardInterrupt:
        print("\nAuf Wiedersehen!")
        break

    if user_query.strip().lower() == 'exit':
        print("Auf Wiedersehen!")
        break

    # Prompt-Vorlage definieren
    prompt = f"""
{conversation_history}
User: {user_query}

Assistant:
"""

    if args.verbose:
        print("\nDebug: Generierter Prompt:")
        print(prompt)

    # Antwort generieren mit dem angegebenen Modell und Temperatur
    try:
        response = runQuery(prompt=prompt, model=args.model,
                                   options={'temperature': args.temperature})
    except Exception as e:
        print(f"Fehler bei der Generierung der Antwort: {e}")
        continue

    # Antwort extrahieren und leere Zeilen entfernen
    assistant_response = response
    non_blank_lines = [line for line in assistant_response.splitlines()
                       if line.strip()]

    if args.verbose:
        print("\nDebug: Antwort vom Modell:")
        print(assistant_response)

    # Antwort ausgeben
    output = '\n'.join(non_blank_lines)  # Antwort vorbereiten
    print(f"\n{args.model}: {output}\n")

    # Konversationshistorie aktualisieren
    conversation_history += f"User: {user_query}\n\nAssistant: {assistant_response}\n\n"