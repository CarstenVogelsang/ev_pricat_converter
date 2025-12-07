# Content Generator

KI-generierte Texte für Online-Shops via OpenRouter API.

**Status:** Geplant

## Zielgruppe
- Kunden
- e-vendo Mitarbeiter

## Funktionen

### Geplant
- **Kategorie-Texte:** Intro/Teaser für Shop-Kategorien
- **SEO-Texte:** Meta-Descriptions, Title-Tags
- **Produkttexte:** Beschreibungen aus Basisdaten generieren

## Technologie

### OpenRouter API
- Zugang zu verschiedenen LLMs (GPT-4, Claude, Llama, etc.)
- Pay-per-use Abrechnung
- API-Key in Config-Tabelle speichern

### Workflow
```
User gibt Eingabe → API-Call an OpenRouter → Ergebnis anzeigen → Optional: Speichern/Exportieren
```

## Datenmodell

### Config-Einträge
```
openrouter_api_key    - API Key (verschlüsselt)
openrouter_model      - Standard-Model (z.B. anthropic/claude-3-haiku)
openrouter_max_tokens - Max. Tokens pro Request
```

### Optional: Generierte Texte speichern
```
generated_content
├── id
├── user_id (FK)
├── content_type (kategorie/seo/produkt)
├── input_text
├── output_text
├── model_used
├── created_at
└── tokens_used
```

## UI/UX

### Mockup: Kategorie-Text Generator
```
┌─────────────────────────────────────────┐
│ Kategorie-Text Generator                │
├─────────────────────────────────────────┤
│ Kategorie: [Spielzeug > Baukästen    ]  │
│ Stil:      [Informativ v]               │
│ Länge:     [Mittel v]                   │
│                                         │
│ [ Generieren ]                          │
├─────────────────────────────────────────┤
│ Ergebnis:                               │
│ ┌─────────────────────────────────────┐ │
│ │ Baukästen fördern die Kreativität   │ │
│ │ und das räumliche Denken von        │ │
│ │ Kindern. In unserem Sortiment...    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [ Kopieren ] [ Neu generieren ]         │
└─────────────────────────────────────────┘
```

## Tasks

| # | Task | Status | Beschreibung |
|---|------|--------|--------------|
| C1 | OpenRouter Integration | ⏳ Offen | API-Service mit httpx |
| C2 | Config-Einträge | ⏳ Offen | API-Key, Model, etc. |
| C3 | Blueprint | ⏳ Offen | Routes für Content Generator |
| C4 | Kategorie-Generator UI | ⏳ Offen | Formular + Ergebnis |
| C5 | SEO-Generator UI | ⏳ Offen | Meta-Description Generator |
| C6 | Produkt-Generator UI | ⏳ Offen | Produkttext aus Basisdaten |
| C7 | History (optional) | ⏳ Offen | Generierte Texte speichern |
