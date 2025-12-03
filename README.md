

# Repository klonen
  
  git clone git@github.com:CarstenVogelsang/ev_pricat_converter.git
  
  cd ev_pricat_converter

  # Python-Umgebung einrichten
  
  python -m venv venv
  
  source venv/bin/activate
  
  pip install -r requirements.txt

  # Datenbank initialisieren und Testdaten laden
  
  flask init-db
  
  flask seed

  # Server starten (optional zum Testen)
  
  python run.py

  Dann in Claude Code starten und z.B. sagen:

  "Lies CLAUDE.md und implementiere Phase 2: pricat_parser.py Service"

  Die CLAUDE.md enthält alle nötigen Infos zu:
  
  - Projektstruktur und Tech-Stack
  - PRICAT-Spalten-Mapping (0-basiert)
  - Elena-Zielformat
  - Was in Phase 2-4 noch zu tun ist
