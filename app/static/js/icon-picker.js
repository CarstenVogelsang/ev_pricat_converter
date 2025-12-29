/**
 * Tabler Icon Picker
 *
 * Zentraler Icon Picker für die Auswahl von Tabler Icons.
 * Wird als Offcanvas-Dialog dargestellt und kann von Modals aus geöffnet werden.
 */

// State
let iconPickerTargetInput = null;
let tablerIcons = [];
let iconPickerOffcanvas = null;
let iconsLoaded = false;

/**
 * Öffnet den Icon Picker für ein bestimmtes Input-Feld
 * @param {string} inputId - Die ID des Ziel-Input-Feldes
 */
async function openIconPicker(inputId) {
    iconPickerTargetInput = document.getElementById(inputId);

    if (!iconPickerTargetInput) {
        console.error('Icon Picker: Input nicht gefunden:', inputId);
        return;
    }

    // Offcanvas-Instanz erstellen falls nicht vorhanden
    const offcanvasEl = document.getElementById('iconPickerOffcanvas');
    if (!offcanvasEl) {
        console.error('Icon Picker: Offcanvas Element nicht gefunden');
        return;
    }

    if (!iconPickerOffcanvas) {
        iconPickerOffcanvas = new bootstrap.Offcanvas(offcanvasEl);
    }

    // Icons laden falls noch nicht geschehen
    if (!iconsLoaded) {
        await loadTablerIcons();
    }

    // Aktuellen Wert vorselektieren
    const currentValue = iconPickerTargetInput.value;
    highlightSelectedIcon(currentValue);

    // Suchfeld leeren
    const searchInput = document.getElementById('iconSearchInput');
    if (searchInput) {
        searchInput.value = '';
    }

    // Alle Icons anzeigen
    renderIcons(tablerIcons);

    // Offcanvas öffnen
    iconPickerOffcanvas.show();

    // Focus auf Suchfeld nach Öffnen
    offcanvasEl.addEventListener('shown.bs.offcanvas', function onShown() {
        searchInput?.focus();
        offcanvasEl.removeEventListener('shown.bs.offcanvas', onShown);
    });
}

/**
 * Lädt die Tabler Icons Liste
 */
async function loadTablerIcons() {
    const statusEl = document.getElementById('iconLoadingStatus');

    try {
        if (statusEl) statusEl.textContent = 'Lade Icons...';

        const response = await fetch('/static/js/tabler-icons-list.json');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        tablerIcons = await response.json();
        iconsLoaded = true;

        if (statusEl) statusEl.textContent = '';
        updateIconCount(tablerIcons.length);

        console.log(`Icon Picker: ${tablerIcons.length} Icons geladen`);

    } catch (error) {
        console.error('Icon Picker: Fehler beim Laden der Icons:', error);
        if (statusEl) statusEl.textContent = 'Fehler beim Laden';

        // Fallback: Minimale Icon-Liste (new format with tags)
        tablerIcons = [
            {name: 'ti-home', tags: ['house', 'building', 'main']},
            {name: 'ti-user', tags: ['person', 'account', 'profile']},
            {name: 'ti-settings', tags: ['config', 'gear', 'preferences']},
            {name: 'ti-search', tags: ['find', 'magnifying', 'glass']},
            {name: 'ti-plus', tags: ['add', 'new', 'create']},
            {name: 'ti-edit', tags: ['pencil', 'modify', 'change']},
            {name: 'ti-trash', tags: ['delete', 'remove', 'bin']},
            {name: 'ti-check', tags: ['done', 'complete', 'success']},
            {name: 'ti-x', tags: ['close', 'cancel', 'remove']},
            {name: 'ti-alert-triangle', tags: ['warning', 'danger', 'error']},
            {name: 'ti-player-play', tags: ['start', 'video', 'music', 'begin']}
        ];
        iconsLoaded = true;
        updateIconCount(tablerIcons.length);
    }

    renderIcons(tablerIcons);
}

/**
 * Rendert die Icon-Liste im Grid
 * @param {Object[]} icons - Array mit Icon-Objekten {name, tags}
 */
function renderIcons(icons) {
    const grid = document.getElementById('iconGrid');
    if (!grid) return;

    if (icons.length === 0) {
        grid.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="ti ti-mood-sad fs-1"></i>
                <p class="mt-2 mb-0">Keine Icons gefunden</p>
            </div>
        `;
        return;
    }

    // Performance: DocumentFragment verwenden
    const fragment = document.createDocumentFragment();

    icons.forEach(iconData => {
        // Support both old format (string) and new format (object)
        const iconName = typeof iconData === 'string' ? iconData : iconData.name;

        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'icon-grid-item';
        item.title = iconName;
        item.onclick = () => selectIcon(iconName);

        const icon = document.createElement('i');
        icon.className = `ti ${iconName}`;
        item.appendChild(icon);

        fragment.appendChild(item);
    });

    grid.innerHTML = '';
    grid.appendChild(fragment);

    updateIconCount(icons.length);
}

/**
 * Filtert Icons nach Suchbegriff (durchsucht Name UND Tags)
 * @param {string} query - Suchbegriff
 */
function filterIcons(query) {
    const searchTerm = query.toLowerCase().trim();

    if (!searchTerm) {
        renderIcons(tablerIcons);
        return;
    }

    const filtered = tablerIcons.filter(iconData => {
        // Support both old format (string) and new format (object)
        if (typeof iconData === 'string') {
            const name = iconData.replace('ti-', '');
            return name.includes(searchTerm);
        }

        // New format with tags
        // 1. Search in icon name (without 'ti-' prefix)
        const name = iconData.name.replace('ti-', '');
        if (name.includes(searchTerm)) {
            return true;
        }

        // 2. Search in tags
        if (iconData.tags && Array.isArray(iconData.tags)) {
            return iconData.tags.some(tag =>
                tag.toLowerCase().includes(searchTerm)
            );
        }

        return false;
    });

    renderIcons(filtered);
}

/**
 * Leert das Suchfeld und zeigt alle Icons
 */
function clearIconSearch() {
    const searchInput = document.getElementById('iconSearchInput');
    if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
    }
    renderIcons(tablerIcons);
}

/**
 * Wählt ein Icon aus und überträgt es ins Ziel-Input
 * @param {string} iconName - Der gewählte Icon-Name (immer mit ti- Prefix)
 */
function selectIcon(iconName) {
    if (!iconPickerTargetInput) {
        console.error('Icon Picker: Kein Ziel-Input definiert');
        return;
    }

    // Prüfen ob das Feld Icons ohne Prefix erwartet
    const stripPrefix = iconPickerTargetInput.dataset.stripPrefix === 'true';
    let valueToSet = iconName;

    if (stripPrefix && iconName.startsWith('ti-')) {
        valueToSet = iconName.substring(3); // Remove 'ti-' prefix
    }

    // Wert ins Input-Feld schreiben
    iconPickerTargetInput.value = valueToSet;

    // Preview aktualisieren
    updateIconPreviewFor(iconPickerTargetInput.id);

    // Change-Event auslösen (für andere Event-Handler)
    iconPickerTargetInput.dispatchEvent(new Event('change', { bubbles: true }));

    // Offcanvas schließen
    if (iconPickerOffcanvas) {
        iconPickerOffcanvas.hide();
    }
}

/**
 * Aktualisiert die Icon-Preview für ein Input-Feld
 * @param {string} inputId - Die ID des Input-Feldes
 */
function updateIconPreviewFor(inputId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(`preview-${inputId}`);

    if (!input || !preview) return;

    let iconName = input.value.trim();

    if (iconName) {
        // Normalisieren: ti- Prefix hinzufügen falls nicht vorhanden
        if (!iconName.startsWith('ti-')) {
            iconName = 'ti-' + iconName;
        }
        preview.innerHTML = `<i class="ti ${iconName}"></i>`;
    } else {
        // Fallback-Icon
        preview.innerHTML = '<i class="ti ti-icons"></i>';
    }
}

/**
 * Hebt das aktuell ausgewählte Icon im Grid hervor
 * @param {string} iconName - Der Icon-Name (mit oder ohne ti- Prefix)
 */
function highlightSelectedIcon(iconName) {
    // Alle Markierungen entfernen
    document.querySelectorAll('.icon-grid-item.selected').forEach(el => {
        el.classList.remove('selected');
    });

    if (!iconName) return;

    // Normalisieren: ti- Prefix hinzufügen falls nicht vorhanden
    let normalizedName = iconName;
    if (!normalizedName.startsWith('ti-')) {
        normalizedName = 'ti-' + normalizedName;
    }

    // Neues Icon markieren
    const grid = document.getElementById('iconGrid');
    if (!grid) return;

    const items = grid.querySelectorAll('.icon-grid-item');
    items.forEach(item => {
        if (item.title === normalizedName) {
            item.classList.add('selected');
            // In den Viewport scrollen
            item.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
}

/**
 * Aktualisiert die Anzeige der Icon-Anzahl
 * @param {number} count - Anzahl der Icons
 */
function updateIconCount(count) {
    const countEl = document.getElementById('iconCount');
    if (countEl) {
        countEl.textContent = count.toLocaleString('de-DE');
    }
}

// Keyboard-Unterstützung für Suche
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('iconSearchInput');
    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (iconPickerOffcanvas) {
                    iconPickerOffcanvas.hide();
                }
            }
        });
    }
});
