# rag
Python Scripts to build a Retrieval Augmented Generation chatbot based on elasticsearch and ollama

## Beschreibung

Mit dieser Serie von Python Scripten wird Schritt für Schritt ein einfaches Retrieval Augmentet Generation (RAG) System erstellt. Ein RAG System besteht aus (1) Einer Retrieval-Komponente, die zu einer gegebenen Anfrage passende Dokumente in einem Index sucht, und (2) einer generativen Komponente (Sprachmodell), dass diese Dokumente bezüglich der Anfrage auswertet und eine Antwort generiert. Das System ist darauf ausgelegt, deutschsprachige Dokumente zu verarbeiten.

Die Technische Umsetzung beruht auf folgenden Komponenten:
- Für die Indizierung der Dokumente und als Vektor-Datenbank wird [Elasticsearch](https://www.elastic.co) verwendet.
- Mit dem Embedding-Modell [XLM-Roberta](https://huggingface.co/transformers/model_doc/xlmroberta.html) werden die Dokumente und die Anfrage semantisch indiziert.
- Ein lokales LLM (Default: [llama3.1](https://huggingface.co/meta-llama)) verarbeitet die Informationen und generiert die Antwort.

Verwendete Python-Bibliotheken:
- ollama: Schnittstelle zu Ollama (Verwaltung lokaler LLMs)
- tika: Text-Extraktion aus PDF, DOCX, HTML und vielen anderen Dateitypen
- requests: https-Requests
- beautifulsoup4: Website Scraping
- elasticsearch: Schnittstelle zu Elasticsearch (Datenbank und Dokumentenindex)
- transformers: Laden und Ausführen von Transformer-Modellen
- torch: Bibliothek für maschinelles Lernen mit GPU-Anbindung
- sentencepiece: Tokenizer, der von XLM-Roberta verwendet wird

## Installation

Externe Komponenten:
1. Installieren Sie [Ollama](https://ollama.com)
2. Installieren Sie [Elasticsearch](https://www.elastic.co)

Python Bibliotheken:
1. Erstellen Sie ein virtuelles Environment (venv): `python3 -m venv venv`
2. Aktivieren Sie das venv: `source venv/bin/activate` (Mac & Linux) bzw. `venv\Scripts\activate` (Windows).
3. Installieren die die Bibliotheken: `pip install -r requirements.txt`

## Ausführung

Die Skripte sind in der Reihenfolge durchnummeriert, in der sie gestartet werden. Die Skripte 01-03 dienen dem inhaltlichen Einstieg bzw. der Vorbereitung. Hier wird Elasticsearch nicht benötigt.

- `01-chat.py` - Startet einen Chat mit einem lokalen Sprachmodell (Default: llama3.1). Dieses Sprachmodell wird einmalig heruntergeladen und lokal gespeichert, was einige Minuten dauern kann.
- `02-chat-pdf.py` - Chatten Sie mit einem PDF Dokument Ihrer Wahl, z.B. dem Berlin-Brandenburger Rahmenlehrplan Informatik Sek II ;)
- `03-scrape-website.py` - Dieses Skript kopiert Dokumente von einer Website in ein lokales Verzeichnis (Web-Scraping).
- `04-build-index.py` - Dokumente (PDF, DOCX, HTML etc.) aus einem lokalen Verzeichnis werden in Elasticsearch gespeichert und indiziert.
- `05-create_chunks.py` - Die Dokumente werden in Blöcke fester Länge geschnitten und in einem eigenen Index abgelegt.
- `06-add-embeddings.py` - Die Dokumenten-Blöcke werden semantisch indiziert und die entsprechenden Embedding-Vektoren im Index abgelegt.
- `07-chat-embedding.py` - Ein RAG-Chat wird gestartet.

## Debugging

- Arbeiten Sie mit den Fehlermeldungen, um zu identifizieren, in welcher Komponente der Fehler auftritt.
- Für zusätzliche Debugging-Informationen starten Sie das Skript mit dem Parameter `--verbose`.

## Modifikationen

Modifizieren Sie die Skripte, um die Technologie kennen zu lernen.

1. Laden Sie ein anderes [lokales Sprachmodell](https://ollama.com/library).
2. Verändern Sie den System-Prompt.
3. Verändern Sie die Temperatur des Sprachmodells.
4. Experimentieren Sie mit unterschiedlichen Dokumentenindizes.


