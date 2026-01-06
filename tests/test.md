Bitte plane zu Projekt "ev247-Plattform" (ID 1) in Komponente "PRD-011: Projektverwaltung" den Task "PRD011-T032: Task als KI Prompt in Zwischenablage".

## Task-Informationen
- **Typ**: Funktion (Neuentwicklung einer fachlichen oder technischen Funktion)
- **Phase**: MVP

## Beschreibung
1. In Task bearbeiten wird neben der Task ID ein Button mit einem Icon angezeigt, um den Task als KI-Prompt in die Zwischenablage zu kopieren. Wie ist der Prompt aufgebaut? Es wird ein Satz generiert, in dieser Art: "Bitte Task mit der Task ID planen. Die Aufgabe ist vom Typ ... (Anmerkung für KI: mit Erklärung aus Hilfe) "

2. In den Settings der Projektverwaltung wird ein Zusatz hinterlegt, der an jeden KI-Prompt für die Zwischenablage angefügt wird. Er lautet (abänderbar): "Sofern die Anforderung/Aufgabe unklar ist, bitte Rückfragen stellen. Den Task nach Erledigung via API Call .... Sofern im Task gesetzt, bei Erledigung ebenfalls einen Changelog-Eintrag erstellen."
Anmerkung an die KI: Verbessere den Satz für die Settings, so wie du ihn benötigst.

---

## Arbeitsanweisungen
Bei Unklarheiten zur Anforderung bitte Rückfragen stellen. 

Nach Erledigung den Task via API auf "Review" setzen:
`curl -X PATCH http://localhost:5001/api/tasks/32 -H "Content-Type: application/json" -d '{"status": "review"}'`

Falls "Bei Erledigung Changelog-Eintrag erstellen" aktiviert ist, muss ein Changelog erstellt werden, der mit dem Task verknüpft ist.