#!/usr/bin/env python3
# coding: utf-8

"""
Dieses Skript ermöglicht es, mit dem Inhalt eines PDF-Dokuments zu interagieren,
indem es ein lokales Sprachmodell verwendet. Es extrahiert den Text aus einer
angegebenen PDF-Datei, fasst diesen zusammen und ermöglicht anschließend eine
Unterhaltung, in der Fragen zum Inhalt des Dokuments gestellt werden können.

Der Benutzer kann verschiedene Parameter anpassen, darunter das zu verwendende
Sprachmodell, die Sprache der Antworten, die Temperatur des Modells und das
Kontextfenster für die Textverarbeitung. Mit dem Flag `-v` oder `--verbose`
können zusätzliche Debugging-Informationen ausgegeben werden.

Das Skript verwendet Apache Tika zum Extrahieren von Text aus PDFs und Ollama als
Client für das Sprachmodell. Es wurde eine robuste Fehlerbehandlung
implementiert, um sicherzustellen, dass der Benutzer bei Fehlern verständliche
Fehlermeldungen erhält.

Verwendung:
./chat-pdf.py myDoc.pdf --model llama3.1 --language deutsch --temperature 0.8
"""

import argparse
import os
import ollama
from tika import parser

# Funktion zum Extrahieren von Text aus einer PDF-Datei
def extract_text_from_pdf(pdf_path):
    try:
        parsed = parser.from_file(pdf_path)
        text = parsed["content"]
        return text
    except Exception as e:
        print(f"Fehler beim Lesen der PDF-Datei '{pdf_path}': {e}")
        exit(1)

# Funktion zum Entfernen leerer Zeilen aus einem Text
def remove_blank_lines(text):
    if text:
        non_blank_lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(non_blank_lines)
    else:
        return ""

# Funktion zum Zusammenfassen von Text mit dem angegebenen Modell und der Sprache
def summarize_text(client, model, summary_prompt):
    try:
        response = client.generate(
            prompt=summary_prompt, model=model, options={'temperature': 0}
        )
        return remove_blank_lines(response['response'])
    except Exception as e:
        print(f"Fehler bei der Zusammenfassung des Textes: {e}")
        exit(1)

# Kommandozeilenargumente für PDF-Pfad, Modell, Sprache, Temperatur, Kontextfenster und verbose
parser = argparse.ArgumentParser(
    description="Interagiere mit einer PDF-Datei mittels eines lokalen Sprachmodells"
)
parser.add_argument("pdf_path", type=str, help="Pfad zur PDF-Datei.")
parser.add_argument("--model", type=str, default="llama3.1",
                    help="Das zu verwendende Sprachmodell (Standard: llama3.1)")
parser.add_argument("--language", type=str, default="deutsch",
                    help="Die Sprache für Antworten und Zusammenfassung (Standard: deutsch)")
parser.add_argument("--temperature", type=float, default=0.8,
                    help="Die Temperatur für Modellantworten (Standard: 0.8)")
parser.add_argument("--context_window", type=int, default=120000,
                    help="Maximale Anzahl von Zeichen aus dem PDF-Inhalt (Standard: 120000)")
parser.add_argument("--summary_prompt", type=str, default=None,
                    help="Der Prompt, der für die Zusammenfassung verwendet wird.")
parser.add_argument("--system_prompt", type=str, default=None,
                    help="Der System-Prompt für die Unterhaltung (Standardwert wird verwendet, falls nicht angegeben).")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Aktiviere ausführliche Ausgabe für Debugging")
args = parser.parse_args()

# Anfangsnachricht ausgeben
pdf_name = os.path.basename(args.pdf_path)
print(f"Lade Modell {args.model} und verarbeite {pdf_name}. Dies kann etwas dauern.")

# Text aus der PDF extrahieren
if args.verbose:
    print("Extrahiere Text aus der PDF-Datei...")
pdf_text = extract_text_from_pdf(args.pdf_path)

# Inhalt kürzen, falls er das Kontextfenster überschreitet
if len(pdf_text) > args.context_window:
    pdf_text = pdf_text[:args.context_window]
    print("Der Inhalt der PDF-Datei wurde gekürzt, um in das Kontextfenster "
          "des Modells zu passen.")
elif args.verbose:
    print(f"Der gesamte Text passt in das Kontextfenster ({len(pdf_text)} Zeichen).")

# Ollama-Client initialisieren
try:
    client = ollama.Client()
except Exception as e:
    print(f"Fehler beim Initialisieren des Ollama-Clients: {e}")
    exit(1)

# Zusammenfassungsprompt vorbereiten
if args.summary_prompt:
    try:
        summary_prompt = args.summary_prompt.format(language=args.language, text=pdf_text)
    except KeyError as e:
        print(f"Fehler: Platzhalter {e} in summary_prompt nicht gefunden.")
        exit(1)
else:
    summary_prompt = (
        f"Summarize the following text in {args.language}. "
        f"Two paragraphs will be enough:\n\n{pdf_text}\n\nSummary:"
    )

# PDF-Text zusammenfassen
if args.verbose:
    print("Fasse den Text zusammen...")
pdf_summary = summarize_text(client, args.model, summary_prompt)

# Zusammenfassung dem Benutzer anzeigen
print(f"{pdf_summary}\n")

# System-Prompt vorbereiten
if args.system_prompt:
    try:
        conversation_history = args.system_prompt.format(text=pdf_text)
    except KeyError as e:
        print(f"Fehler: Platzhalter {e} in system_prompt nicht gefunden.")
        exit(1)
else:
    conversation_history = (
        f"You are a helpful assistant and inform the user about the following document:\n\n"
        f"{pdf_text}\n\nNow take the user's question."
    )
if args.verbose:
    print("Konversationsverlauf initialisiert.")

# Chat-Schleife
while True:
    try:
        user_query = input("Du sagst: ")
    except EOFError:
        print("Auf Wiedersehen!")
        break
    except KeyboardInterrupt:
        print("\nAuf Wiedersehen!")
        break

    if user_query.lower() == 'exit':
        print("Auf Wiedersehen!")
        break

    # Prompt definieren
    prompt = f"""
{conversation_history}

User: {user_query}

Assistant:
"""

    # Antwort generieren
    if args.verbose:
        print("Generiere Antwort...")
    try:
        response = client.generate(
            prompt=prompt, model=args.model, options={'temperature': args.temperature}
        )
        assistant_response = remove_blank_lines(response['response'])
    except Exception as e:
        print(f"Fehler beim Generieren der Antwort: {e}")
        continue

    # Antwort ausgeben
    print(f"\n{args.model}: {assistant_response}\n")

    # Konversationsverlauf aktualisieren
    conversation_history += f"\nUser: {user_query}\n\nAssistant: {assistant_response}\n"