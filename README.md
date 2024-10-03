# rag
Python Scripts to build a Retrieval Augmented Generation chatbot based on elasticsearch and ollama

## Beschreibung

Mit dieser Serie von Python Scripten wird Schritt für Schritt ein einfaches Retrieval Augmentet Generation (RAG) System erstellt. Ein RAG System besteht aus (1) Einer Retrieval-Komponente, die zu einer gegebenen Anfrage passende Dokumente in einem Index sucht, und (2) einer generativen Komponente (Sprachmodell), dass diese Dokumente bezüglich der Anfrage auswertet und eine Antwort generiert. Das System ist darauf ausgelegt, deutschsprachige Dokumente zu verarbeiten.

Die Technische Umsetzung beruht auf folgenden Komponenten:
- Für die Indizierung der Dokumente und als Vektor-Datenbank wird [Elasticsearch](https://www.elastic.co) verwendet.
- Mit dem Embedding-Modell [XLM-Roberta](https://huggingface.co/FacebookAI/xlm-roberta-base) werden die Dokumente und die Anfrage semantisch indiziert.
- Ein lokales LLM (Default: [llama3.1](https://huggingface.co/meta-llama)) verarbeitet die Informationen und generiert die Antwort.

Verwendete Python-Bibliotheken:
- **ollama**: Schnittstelle zu Ollama (Verwaltung lokaler LLMs)
- **tika**: Text-Extraktion aus PDF, DOCX, HTML und vielen anderen Dateitypen
- **requests**: https-Requests
- **beautifulsoup4**: Website Scraping
- **elasticsearch**: Schnittstelle zu Elasticsearch (Datenbank und Dokumentenindex)
- **transformers**: Laden und Ausführen von Transformer-Modellen
- **torch**: Bibliothek für maschinelles Lernen mit GPU-Anbindung
- **sentencepiece**: Tokenizer, der von XLM-Roberta verwendet wird

## Installation

1. Installieren Sie [Ollama](https://ollama.com)
2. Installieren Sie [Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/install-elasticsearch.html)
3. Installieren die die Bibliotheken: `pip install -r requirements.txt`

## Ausführung

Die Skripte sind in der Reihenfolge durchnummeriert, in der sie gestartet werden. Die Skripte 01-03 dienen dem inhaltlichen Einstieg bzw. der Vorbereitung. Elasticsearch und XLM-Roberta werden ab Skript 04 bzw. 05 benötigt.

- `01-chat.py` - Startet einen Chat mit einem lokalen Sprachmodell (Default: llama3.1). Dieses Sprachmodell wird einmalig heruntergeladen und lokal gespeichert, was einige Minuten dauern kann.
- `02-chat-pdf.py` - Chatten Sie mit einem PDF Dokument Ihrer Wahl
- `03-scrape-website.py` - Dieses Skript kopiert Dokumente von einer Website in ein lokales Verzeichnis (Web-Scraping).
- `04-build-index.py` - Dokumente (PDF, DOCX, HTML etc.) aus einem lokalen Verzeichnis werden in Elasticsearch gespeichert und indiziert.
- `05-create_chunks.py` - Die Dokumente werden in Blöcke fester Länge geschnitten und in einem eigenen Index abgelegt.
- `06-add-embeddings.py` - Die Dokumenten-Blöcke werden semantisch indiziert und die entsprechenden Embedding-Vektoren im Index abgelegt.
- `07-chat-embedding.py` - Ein RAG-Chat wird gestartet.

## Debugging

- Arbeiten Sie mit den Fehlermeldungen, um zu identifizieren, in welcher Komponente der Fehler auftritt.
- Für zusätzliche Debugging-Informationen starten Sie das Skript mit dem Parameter `--verbose`.

----

## Beobachtungen

- Für Anfragen zu Personen gibt es schlechte Treffer. Vermutung: die ca. 3-5 Tokens, die einem Namen entsprechen, gehen in der Summe der 512 Tokens unter, aus denen ein Block besteht, unter.
- Ein Scraping der PzA Website besteht aus ca. 300 Dokumenten, daraus ergeben sich ca. 1300 Blöcke a 512 Tokens. Darunter auch viele für unseren Anwendungsfall irrelevante Informationen.
- Llama3.1 verarbeitet Anweisungen auf Englisch deutlich besser. Wir müssen das Modell auf Englisch instruieren, dass es Deutsche Dokumente verarbeitet und auf Deutsch antworten soll.

## Vorschläge zur Weiterentwicklung

- Das Anwendungszenario nachschärfen: was sind typische Anfragen und darauf erwartete Antworten?
- Entwurf eines Benchmarks: Katalog aus vorbildlichen Antworten
- Für Expert:innen: welche alternative Ansätze gibt es zur Lösung des Problems?
- Die Datenbasis vergrößern
- Experimentieren, wie und welche Dokumente der Website sich sinnvoll in die Datenbasis einbinden lassen.
- Optimierung von Parametern: Temperatur, Blockgröße, Anzahl der Dokumente
- Optimierung der Prompts
- Einsatz anderer Embedding-Modelle, die auf deutschem Vokabular trainiert sind.
- Eigennamen herausfiltern und Dokumente per Volltextsuche in Elasticsearch suchen lassen.

## Ergebnissicherung Workshop

Alternative Ansätze zur Realisierung:
- zu Elasticsearch: llama-index (Python library) -> muss progammiert werden
- zu ollama: Api-key z.B. von KISSKI.de -> im Leistungskatalog kostenlos mit Ticket anfragen -> Skript 01-chat-ai.py mit API key (manuell 'c' anhängen) --> hier könnt ihr bei academic cloud direkt gucken

Weitere Ideen für Workshop:
- das ganze Set-Up auf einem Raspberry Pi laufen lassen mit kleinem Monitor

Gruppe Prompts / Use Cases:
- Fokus auf Nutzer*innen Prompts
- Aufteilung in neue Mitarbeiter*innen und etablierte Mitarbeitende - unterschiedliche Fragestellungen sind relevant
- + generelle Unternehmensabläufe und -prozesse
 
Gruppe Prompts / technisch: 
- Wenn Infos nicht auffindbar sind: Speicherung mit den gestellten Anfragen (+ Hinweis: Ist es ok, wenn deine Anfrage gespeichert wird) und Abfrage von gefundenen Lösungen außerhalb des RAG -> Sammlung zu ungelösten Fragen in einer Datei und Einspeisung weiterer Daten in die Wissensdatenbank

Gruppe Cross Referencing:
- mit Script Informationen aus Referenzen scrapen und dann in die Dokumente wieder einfügen
- bei Politik zum Anfassen ggf. relevant, wenn in Dokumenten rechtliche Aspekte wie z.B. Arbeitsrecht referenziert wird

Gruppe eigene Uniwebsite:
- Ausprobieren dort mit dem Prototypen: hier wurden alle Links auf der Website automatisch auch mitgescraped

Gruppe englisch vs. deutsch:
- Ergebnis: auf englisch funktioniert es deutlich besser als auf deutsch 


  





