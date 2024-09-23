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

Das Skript verwendet PyMuPDF zum Extrahieren von Text aus PDFs und Ollama als
Client für das Sprachmodell. Es wurde eine robuste Fehlerbehandlung
implementiert, um sicherzustellen, dass der Benutzer bei Fehlern verständliche
Fehlermeldungen erhält.

Verwendung:
./chat-pdf.py myDoc.pdf --model llama3.1 --language deutsch --temperature 0.8
"""

import fitz  # PyMuPDF
import argparse
import os
import ollama

# Funktion zum Extrahieren von Text aus einer PDF-Datei
def extract_text_from_pdf(pdf_path):
    try:
        with fitz.open(pdf_path) as doc:
            text = ""
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        print(f"Fehler beim Lesen der PDF-Datei '{pdf_path}': {e}")
        exit(1)

# Funktion zum Entfernen leerer Zeilen aus einem Text
def remove_blank_lines(text):
    non_blank_lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(non_blank_lines)

# Funktion zum Zusammenfassen von Text mit dem angegebenen Modell und der Sprache
def summarize_text(text, client, model, language):
    try:
        summary_prompt = (
            f"Fasse den folgenden Text in {language} zusammen. "
            f"Zwei Absätze reichen aus:\n\n{text}\n\nZusammenfassung:"
        )
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

# PDF-Text zusammenfassen
if args.verbose:
    print("Fasse den Text zusammen...")
pdf_summary = summarize_text(pdf_text, client, args.model, args.language)

# Zusammenfassung dem Benutzer anzeigen
print(f"{pdf_summary}\n")

# Konversationsverlauf mit dem kodierten Inhalt initialisieren
conversation_history = (
    f"Du bist ein hilfreicher Assistent und informierst den Benutzer über das "
    f"folgende Dokument:\n\n{pdf_text}\n\nBitte beantworte nun die Fragen des Benutzers."
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

Benutzer: {user_query}

Assistent:
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
    conversation_history += f"\nBenutzer: {user_query}\n\nAssistent: {assistant_response}\n"