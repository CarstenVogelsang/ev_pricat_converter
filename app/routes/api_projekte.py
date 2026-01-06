"""API Blueprint for project management (PRD-011).

Provides JSON/Markdown endpoints for Claude Code integration.
These endpoints allow AI agents to read PRDs, tasks, and changelogs.
"""
import re
from flask import Blueprint, jsonify, Response, request
from datetime import datetime
from flask_login import login_required, current_user
from app.models import (
    Projekt, Komponente, Task, ChangelogEintrag,
    TaskStatus, TaskPhase, Config, TaskKommentar
)


def parse_task_nummer(task_nummer):
    """Parse task number like PRD011-T020.

    Args:
        task_nummer: Task number string (e.g. 'PRD011-T020')

    Returns:
        tuple (prd_nummer, task_id) or None if invalid format.

    Example:
        >>> parse_task_nummer('PRD011-T020')
        ('011', 20)
    """
    match = re.match(r'^PRD(\d{3})-T(\d{3})$', task_nummer)
    if match:
        return match.group(1), int(match.group(2))
    return None

api_projekte_bp = Blueprint('api_projekte', __name__, url_prefix='/api')


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@api_projekte_bp.route('/projekte', methods=['GET'])
def list_projekte():
    """List all projects.

    Returns JSON array of project summaries.

    Usage:
        curl http://localhost:5001/api/projekte
    """
    projekte = Projekt.query.filter_by(aktiv=True).order_by(Projekt.name).all()
    return jsonify([p.to_dict() for p in projekte])


@api_projekte_bp.route('/projekte/<int:id>', methods=['GET'])
def get_projekt(id):
    """Get project details including components.

    Args:
        id: Project ID

    Returns JSON with project details and component list.

    Usage:
        curl http://localhost:5001/api/projekte/1
    """
    projekt = Projekt.query.get_or_404(id)
    return jsonify(projekt.to_dict(include_komponenten=True))


# =============================================================================
# COMPONENT ENDPOINTS
# =============================================================================

@api_projekte_bp.route('/komponenten', methods=['GET'])
def list_komponenten():
    """List all components across all projects.

    Query params:
        projekt_id: Filter by project
        typ: Filter by type (modul/basisfunktion/entity)
        phase: Filter by current phase (poc/mvp/v1/v2)

    Usage:
        curl http://localhost:5001/api/komponenten
        curl http://localhost:5001/api/komponenten?projekt_id=1
        curl http://localhost:5001/api/komponenten?typ=modul
    """
    query = Komponente.query.filter_by(status='aktiv')

    # Apply filters
    if request.args.get('projekt_id'):
        query = query.filter_by(projekt_id=int(request.args.get('projekt_id')))
    if request.args.get('typ'):
        query = query.filter_by(typ=request.args.get('typ'))
    if request.args.get('phase'):
        query = query.filter_by(aktuelle_phase=request.args.get('phase'))

    komponenten = query.order_by(Komponente.sortierung).all()
    return jsonify([k.to_dict() for k in komponenten])


@api_projekte_bp.route('/komponenten/<int:id>', methods=['GET'])
def get_komponente(id):
    """Get component details.

    Args:
        id: Component ID

    Usage:
        curl http://localhost:5001/api/komponenten/1
    """
    komponente = Komponente.query.get_or_404(id)
    return jsonify(komponente.to_dict(include_prd=True, include_tasks=True))


@api_projekte_bp.route('/komponenten/<int:id>/prd', methods=['GET'])
def get_komponente_prd(id):
    """Get PRD content as Markdown.

    Args:
        id: Component ID

    Returns PRD content with Content-Type: text/markdown

    Usage:
        curl http://localhost:5001/api/komponenten/1/prd
    """
    komponente = Komponente.query.get_or_404(id)

    if not komponente.prd_inhalt:
        return Response(
            f"# {komponente.prd_bezeichnung}: {komponente.name}\n\n"
            f"*Kein PRD-Inhalt vorhanden.*",
            mimetype='text/markdown'
        )

    return Response(komponente.prd_inhalt, mimetype='text/markdown')


@api_projekte_bp.route('/komponenten/<int:id>/tasks', methods=['GET'])
def get_komponente_tasks(id):
    """Get tasks for a component.

    Args:
        id: Component ID

    Query params:
        phase: Filter by phase (poc/mvp/v1/v2)
        status: Filter by status (backlog/geplant/in_arbeit/review/erledigt)

    Usage:
        curl http://localhost:5001/api/komponenten/1/tasks
        curl http://localhost:5001/api/komponenten/1/tasks?phase=mvp
        curl http://localhost:5001/api/komponenten/1/tasks?status=in_arbeit
    """
    komponente = Komponente.query.get_or_404(id)
    query = komponente.tasks

    # Apply filters
    if request.args.get('phase'):
        query = query.filter_by(phase=request.args.get('phase'))
    if request.args.get('status'):
        query = query.filter_by(status=request.args.get('status'))

    tasks = query.order_by(Task.sortierung).all()
    return jsonify([t.to_dict(include_beschreibung=True) for t in tasks])


@api_projekte_bp.route('/komponenten/<int:id>/changelog', methods=['GET'])
def get_komponente_changelog(id):
    """Get changelog for a component as Markdown.

    Args:
        id: Component ID

    Query params:
        format: 'json' or 'markdown' (default: markdown)
        version: Filter by version

    Usage:
        curl http://localhost:5001/api/komponenten/1/changelog
        curl http://localhost:5001/api/komponenten/1/changelog?format=json
    """
    komponente = Komponente.query.get_or_404(id)

    # Get changelog entries
    query = komponente.changelog_eintraege
    if request.args.get('version'):
        query = query.filter_by(version=request.args.get('version'))

    eintraege = query.order_by(ChangelogEintrag.erstellt_am.desc()).all()

    # Return JSON if requested
    if request.args.get('format') == 'json':
        return jsonify([e.to_dict() for e in eintraege])

    # Generate Markdown changelog
    if not eintraege:
        return Response(
            f"# Changelog: {komponente.name}\n\n*Noch keine Einträge.*",
            mimetype='text/markdown'
        )

    # Group by version
    by_version = {}
    for e in eintraege:
        if e.version not in by_version:
            by_version[e.version] = []
        by_version[e.version].append(e)

    # Generate Markdown
    lines = [f"# Changelog: {komponente.name}\n"]
    for version, entries in by_version.items():
        lines.append(f"\n## {version}\n")

        # Group by category
        by_kategorie = {}
        for e in entries:
            if e.kategorie not in by_kategorie:
                by_kategorie[e.kategorie] = []
            by_kategorie[e.kategorie].append(e)

        for kategorie in ['added', 'changed', 'fixed', 'removed']:
            if kategorie in by_kategorie:
                lines.append(f"\n### {kategorie.capitalize()}\n")
                for e in by_kategorie[kategorie]:
                    lines.append(e.to_markdown())

    return Response('\n'.join(lines), mimetype='text/markdown')


# =============================================================================
# TASK ENDPOINTS
# =============================================================================

@api_projekte_bp.route('/tasks/<int:id>', methods=['GET'])
def get_task(id):
    """Get task details.

    Args:
        id: Task ID

    Usage:
        curl http://localhost:5001/api/tasks/1
    """
    task = Task.query.get_or_404(id)
    return jsonify(task.to_dict(include_beschreibung=True))


@api_projekte_bp.route('/tasks/by-nummer/<task_nummer>', methods=['GET'])
def get_task_by_nummer(task_nummer):
    """Get task by readable task number (e.g. PRD011-T020).

    This endpoint allows Claude Code to fetch a task using the human-readable
    task number format instead of the numeric database ID.

    Args:
        task_nummer: Task number in format PRD{3digits}-T{3digits}

    Usage:
        curl http://localhost:5001/api/tasks/by-nummer/PRD011-T020
    """
    parsed = parse_task_nummer(task_nummer)
    if not parsed:
        return jsonify({
            'error': f'Ungültiges Task-Nummer-Format: {task_nummer}',
            'expected_format': 'PRD{3digits}-T{3digits}',
            'example': 'PRD011-T020'
        }), 400

    prd_nummer, task_id = parsed
    task = Task.query.get_or_404(task_id)

    # Validate PRD number matches
    if task.komponente.prd_nummer != prd_nummer:
        return jsonify({
            'error': f'Task {task_id} gehört nicht zu PRD-{prd_nummer}',
            'actual_prd': task.komponente.prd_nummer,
            'task_nummer': task.task_nummer
        }), 404

    return jsonify(task.to_dict(include_beschreibung=True))


@api_projekte_bp.route('/tasks/<int:id>', methods=['PATCH'])
def update_task(id):
    """Update task fields.

    Allows updating task status, assignment, priority, and description.
    Used by Claude Code to set task status to 'in_arbeit' when starting work.

    Args:
        id: Task ID

    Request body (JSON):
        status: 'backlog'|'geplant'|'in_arbeit'|'review'|'erledigt'
        zugewiesen_an: User ID (integer) or null
        prioritaet: 'niedrig'|'mittel'|'hoch'|'kritisch'
        beschreibung: Markdown text
        komponente_id: Component ID (move task to different component)

    Usage:
        curl -X PATCH http://localhost:5001/api/tasks/20 \\
             -H "Content-Type: application/json" \\
             -d '{"status": "in_arbeit"}'
    """
    from app import db

    task = Task.query.get_or_404(id)
    data = request.get_json() or {}

    # Track what was updated
    updated_fields = []

    # Update allowed fields
    if 'status' in data:
        old_status = task.status
        task.status = data['status']
        updated_fields.append(f'status: {old_status} → {task.status}')

    if 'zugewiesen_an' in data:
        task.zugewiesen_an = data['zugewiesen_an']
        updated_fields.append(f'zugewiesen_an: {task.zugewiesen_an}')

    if 'prioritaet' in data:
        task.prioritaet = data['prioritaet']
        updated_fields.append(f'prioritaet: {task.prioritaet}')

    if 'beschreibung' in data:
        task.beschreibung = data['beschreibung']
        updated_fields.append('beschreibung')

    if 'titel' in data:
        task.titel = data['titel']
        updated_fields.append(f'titel: {task.titel}')

    if 'ist_archiviert' in data:
        task.ist_archiviert = data['ist_archiviert']
        updated_fields.append(f'ist_archiviert: {task.ist_archiviert}')

    # PRD011-T056: Task in andere Komponente verschieben
    if 'komponente_id' in data:
        neue_komponente = Komponente.query.get(data['komponente_id'])
        if not neue_komponente:
            return jsonify({'error': 'Komponente nicht gefunden', 'success': False}), 404
        # Prüfen ob gleiche Projekt-ID
        if neue_komponente.projekt_id != task.komponente.projekt_id:
            return jsonify({
                'error': 'Task kann nur innerhalb desselben Projekts verschoben werden',
                'success': False
            }), 400
        alte_komponente_name = task.komponente.name
        task.komponente_id = data['komponente_id']
        updated_fields.append(f'komponente: {alte_komponente_name} → {neue_komponente.name}')

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Task aktualisiert: {", ".join(updated_fields)}' if updated_fields else 'Keine Änderungen',
        'task': task.to_dict(include_beschreibung=True)
    })


@api_projekte_bp.route('/tasks/<int:id>/erledigen', methods=['POST'])
def task_erledigen(id):
    """Mark a task as completed.

    This will:
    1. Set task status to 'erledigt'
    2. Set erledigt_am timestamp
    3. Optionally create a changelog entry

    Args:
        id: Task ID

    Request body (JSON, optional):
        create_changelog: boolean (default: true)
        changelog_kategorie: 'added'|'changed'|'fixed'|'removed' (default: 'added')
        changelog_beschreibung: string (default: task title)

    Usage:
        curl -X POST http://localhost:5001/api/tasks/1/erledigen
        curl -X POST http://localhost:5001/api/tasks/1/erledigen \
             -H "Content-Type: application/json" \
             -d '{"create_changelog": true, "changelog_kategorie": "fixed"}'
    """
    from app import db

    task = Task.query.get_or_404(id)

    if task.ist_erledigt:
        return jsonify({
            'success': False,
            'message': 'Task ist bereits erledigt',
            'task': task.to_dict()
        }), 400

    # Mark task as completed
    task.erledigen()

    # Create changelog entry if requested
    changelog_entry = None
    data = request.get_json() or {}
    create_changelog = data.get('create_changelog', True)

    if create_changelog:
        changelog_entry = ChangelogEintrag.create_from_task(
            task,
            kategorie=data.get('changelog_kategorie'),
            beschreibung=data.get('changelog_beschreibung'),
        )
        db.session.add(changelog_entry)

    db.session.commit()

    result = {
        'success': True,
        'message': 'Task als erledigt markiert',
        'task': task.to_dict()
    }
    if changelog_entry:
        result['changelog_entry'] = changelog_entry.to_dict()

    return jsonify(result)


@api_projekte_bp.route('/tasks/<int:id>/prompt', methods=['GET'])
def task_prompt(id):
    """Generate AI prompt for a task (PRD011-T032).

    Creates a structured prompt containing task information that can be
    copied to clipboard for use with Claude Code or other AI assistants.

    Args:
        id: Task ID

    Returns:
        JSON with generated prompt and task number

    Usage:
        curl http://localhost:5001/api/tasks/32/prompt
    """
    task = Task.query.get_or_404(id)

    # Load project and component context (PRD011-T044)
    komponente = task.komponente
    projekt = komponente.projekt

    # Get prompt suffix from config
    config = Config.query.filter_by(key='projektverwaltung_ki_prompt_suffix').first()
    suffix = config.value if config else ''

    # Replace placeholders
    suffix = suffix.replace('{task_id}', str(task.id))

    # Build the prompt with project/component context (PRD011-T044)
    prompt = f"""Bitte plane zu Projekt "{projekt.name}" (ID {projekt.id}) in Komponente "{komponente.prd_bezeichnung}: {komponente.name}" den Task "{task.task_nummer}: {task.titel}".

## Task-Informationen
- **Typ**: {task.typ_label}{f' ({task.typ_beschreibung})' if task.typ_beschreibung else ''}
- **Phase**: {task.phase.upper() if task.phase else 'Nicht gesetzt'}

## Beschreibung
{task.beschreibung or 'Keine Beschreibung vorhanden.'}

---

## Arbeitsanweisungen
{suffix}"""

    return jsonify({
        'prompt': prompt,
        'task_nummer': task.task_nummer,
        'task_id': task.id
    })


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@api_projekte_bp.route('/komponenten-uebersicht', methods=['GET'])
def komponenten_uebersicht():
    """Get a quick overview of all components with their IDs.

    Useful for Claude Code to quickly find component IDs.

    Usage:
        curl http://localhost:5001/api/komponenten-uebersicht
    """
    komponenten = Komponente.query.filter_by(status='aktiv') \
        .order_by(Komponente.prd_nummer).all()

    return jsonify([{
        'id': k.id,
        'prd_nummer': k.prd_nummer,
        'prd_bezeichnung': k.prd_bezeichnung,
        'name': k.name,
        'typ': k.typ,
        'aktuelle_phase': k.aktuelle_phase,
    } for k in komponenten])


# =============================================================================
# TASK COMMENTS API (PRD011-T055)
# =============================================================================

@api_projekte_bp.route('/tasks/<int:id>/kommentare', methods=['GET'])
def task_kommentare_list(id):
    """List all comments for a task.

    Args:
        id: Task ID

    Query params:
        typ: Filter by type (review/frage/hinweis/kommentar)
        erledigt: Filter by completion status (true/false)

    Usage:
        curl http://localhost:5001/api/tasks/54/kommentare
        curl http://localhost:5001/api/tasks/54/kommentare?typ=review
        curl http://localhost:5001/api/tasks/54/kommentare?erledigt=false
    """
    task = Task.query.get_or_404(id)
    query = task.kommentare

    # Apply filters
    if request.args.get('typ'):
        query = query.filter_by(typ=request.args.get('typ'))
    if request.args.get('erledigt') is not None:
        erledigt = request.args.get('erledigt').lower() == 'true'
        query = query.filter_by(erledigt=erledigt)

    return jsonify({
        'task_id': task.id,
        'task_nummer': task.task_nummer,
        'anzahl': query.count(),
        'kommentare': [k.to_dict() for k in query.all()]
    })


@api_projekte_bp.route('/tasks/<int:id>/kommentare', methods=['POST'])
@login_required
def task_kommentar_create(id):
    """Add a comment to a task.

    Args:
        id: Task ID

    Request body (JSON):
        typ: 'review'|'frage'|'hinweis'|'kommentar' (default: 'kommentar')
        inhalt: Comment text (required)

    Usage:
        curl -X POST http://localhost:5001/api/tasks/54/kommentare \\
             -H "Content-Type: application/json" \\
             -d '{"typ": "review", "inhalt": "Icon-Farbe bei Otto anpassen"}'
    """
    from app import db

    task = Task.query.get_or_404(id)
    data = request.get_json()

    if not data or not data.get('inhalt'):
        return jsonify({'error': 'Inhalt ist erforderlich'}), 400

    kommentar = TaskKommentar(
        task_id=task.id,
        user_id=current_user.id,
        typ=data.get('typ', 'kommentar'),
        inhalt=data.get('inhalt', '')
    )
    db.session.add(kommentar)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Kommentar vom Typ "{kommentar.typ}" hinzugefügt',
        'kommentar': kommentar.to_dict()
    }), 201


@api_projekte_bp.route('/kommentare/<int:id>/toggle-erledigt', methods=['POST'])
@login_required
def kommentar_toggle_erledigt(id):
    """Toggle completion status of a comment.

    Args:
        id: Comment ID

    Usage:
        curl -X POST http://localhost:5001/api/kommentare/1/toggle-erledigt
    """
    from app import db

    kommentar = TaskKommentar.query.get_or_404(id)

    kommentar.erledigt = not kommentar.erledigt
    kommentar.erledigt_am = datetime.utcnow() if kommentar.erledigt else None
    db.session.commit()

    status = 'erledigt' if kommentar.erledigt else 'offen'
    return jsonify({
        'success': True,
        'message': f'Kommentar als {status} markiert',
        'kommentar': kommentar.to_dict()
    })


@api_projekte_bp.route('/kommentare/<int:id>', methods=['PUT'])
@login_required
def kommentar_update(id):
    """Update a comment (only own comments).

    Args:
        id: Comment ID

    Request body (JSON):
        inhalt: New comment text
        typ: New comment type (optional)

    Usage:
        curl -X PUT http://localhost:5001/api/kommentare/1 \\
             -H "Content-Type: application/json" \\
             -d '{"inhalt": "Updated comment text"}'
    """
    from app import db

    kommentar = TaskKommentar.query.get_or_404(id)

    # Only allow editing own comments
    if kommentar.user_id != current_user.id:
        return jsonify({'error': 'Nur eigene Kommentare können bearbeitet werden'}), 403

    data = request.get_json()
    if 'inhalt' in data:
        kommentar.inhalt = data['inhalt']
    if 'typ' in data:
        kommentar.typ = data['typ']

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Kommentar aktualisiert',
        'kommentar': kommentar.to_dict()
    })


@api_projekte_bp.route('/kommentare/<int:id>', methods=['DELETE'])
@login_required
def kommentar_delete(id):
    """Delete a comment (only own comments).

    Args:
        id: Comment ID

    Usage:
        curl -X DELETE http://localhost:5001/api/kommentare/1
    """
    from app import db

    kommentar = TaskKommentar.query.get_or_404(id)

    # Only allow deleting own comments
    if kommentar.user_id != current_user.id:
        return jsonify({'error': 'Nur eigene Kommentare können gelöscht werden'}), 403

    task_id = kommentar.task_id
    db.session.delete(kommentar)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Kommentar gelöscht',
        'task_id': task_id
    })


@api_projekte_bp.route('/tasks/<int:id>/review-prompt', methods=['GET'])
def task_review_prompt(id):
    """Generate review prompt from non-completed review comments (PRD011-T055).

    Creates a structured prompt containing task information and all open
    review comments. Used for iterative review workflow with Claude Code.

    Important: Only review comments with erledigt=False are included!

    Args:
        id: Task ID

    Query params:
        auto_status: 'true' to automatically change status to 'in_arbeit' (default: true)

    Returns:
        JSON with generated review prompt and metadata

    Usage:
        curl http://localhost:5001/api/tasks/54/review-prompt
        curl http://localhost:5001/api/tasks/54/review-prompt?auto_status=false
    """
    from app import db

    task = Task.query.get_or_404(id)
    komponente = task.komponente
    projekt = komponente.projekt

    # Get only non-completed review comments
    review_kommentare = task.review_kommentare

    if not review_kommentare:
        return jsonify({
            'error': 'Keine offenen Review-Kommentare vorhanden',
            'task_id': task.id,
            'task_nummer': task.task_nummer,
            'hinweis': 'Es gibt keine Review-Kommentare mit erledigt=False'
        }), 400

    # Format review comments
    kommentare_text = "\n".join([
        f"- {k.inhalt}" for k in review_kommentare
    ])

    # Get config suffix
    config = Config.query.filter_by(
        key='projektverwaltung_review_prompt_suffix'
    ).first()
    suffix = config.value if config else ''

    prompt = f"""## Review für Task {task.task_nummer}

**Projekt:** {projekt.name}
**Komponente:** {komponente.prd_bezeichnung}: {komponente.name}
**Task:** {task.titel}

### Original-Beschreibung
{task.beschreibung or 'Keine Beschreibung'}

### Review-Anmerkungen ({len(review_kommentare)} offene Punkte)
{kommentare_text}

---

Bitte bearbeite die obigen Review-Punkte. Setze den Task anschließend auf Status "review".

{suffix}"""

    # Auto-update status to in_arbeit (unless disabled)
    auto_status = request.args.get('auto_status', 'true').lower() != 'false'
    status_geaendert = False

    if auto_status and task.status == 'review':
        task.status = 'in_arbeit'
        db.session.commit()
        status_geaendert = True

    return jsonify({
        'prompt': prompt,
        'task_nummer': task.task_nummer,
        'task_id': task.id,
        'anzahl_review_punkte': len(review_kommentare),
        'status_geaendert': status_geaendert,
        'neuer_status': task.status if status_geaendert else None
    })
