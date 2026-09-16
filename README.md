# zynthec Apps

Eigene SideStore-/AltStore-Quelle mit miPet und den offiziellen SideInstaller-Releases von FrizzleM.

**Quell-URL:** https://raw.githubusercontent.com/zynthec-dev/zynthec-apps-altsource/main/source.json

In SideStore unter Sources diese URL hinzufügen.

## Neue Apps und Updates veröffentlichen

1. Unter **Releases → Draft a new release** einen beliebigen eindeutigen Tag vergeben.
2. Eine oder mehrere `.ipa`-Dateien als Release-Assets hochladen, Titel und Beschreibung ergänzen.
3. **Publish release** wählen. Der Workflow **Sync all IPA releases** übernimmt neue Apps und Updates automatisch.

Kein manueller Eintrag in `source.json` erforderlich. Bundle-ID, App-Name, Version, Build, Mindest-iOS-Version und Berechtigungen werden aus der IPA gelesen. Dateiname und Release-Tag dürfen frei gewählt werden. Für ein installierbares Update muss die IPA selbst eine erhöhte Version/Buildnummer enthalten; Umbenennen allein ändert diese nicht.

Veröffentlichte Beta-/Prerelease-Releases werden ebenfalls angeboten; Entwürfe nicht. Für dieselbe Bundle-ID/Version/Build-Kombination gewinnt die neueste Veröffentlichung. Jede App erhält zunächst das Quell-Icon als Platzhalter. Eigene Icons unter `icons/` hochladen und ihre Raw-URL optional in `apps.json` setzen.

## Automatische Pflege

- Veröffentlichungen, Bearbeitungen und Löschungen lösen einen vollständigen Abgleich aus.
- Zusätzlich stündlich zur Minute 17: nachträglich hochgeladene, ersetzte oder umbenannte Assets erkennen. GitHub kann geplante Läufe verzögern.
- Sofortiger manueller Abgleich: **Actions → Sync all IPA releases → Run workflow**.
- Änderungen an Skripten, Workflows oder `apps.json` starten ebenfalls einen Abgleich.
- Gelöschte Releases/Assets verschwinden aus der Quelle; Apps ohne verbleibende Veröffentlichung werden entfernt.
- **Update SideInstaller source** prüft alle sechs Stunden das neueste stabile Original-Release. Die IPA wird direkt vom ursprünglichen Projekt bezogen.
- Beide Workflows teilen eine Ausführungssperre und aktualisieren `source.json` nur nach erfolgreicher Prüfung.

Bei fehlerhaften IPAs bleibt der letzte gültige Katalog erhalten und der Workflow schlägt mit einer Fehlermeldung fehl. Größen und vorhandene SHA-256-Prüfsummen werden überprüft. IPAs mit eingebautem miPet-API-Key oder Provisioning-Profilen werden nicht indexiert. Dies ist kein allgemeiner Geheimnis-Scanner: vor einem öffentlichen Upload immer selbst sicherstellen, dass keine Zugangsdaten enthalten sind. Nachträgliches Indexieren kann einen bereits öffentlichen Upload nicht verhindern.

## Optionale Darstellung

`apps.json` enthält Anpassungen nach Bundle-ID. Erlaubt sind `name`, `developerName`, `localizedDescription`, `iconURL` und `category`:

```json
{
  "de.example.app": {
    "name": "Meine App",
    "developerName": "zynthec",
    "localizedDescription": "Beschreibung meiner App.",
    "iconURL": "https://raw.githubusercontent.com/zynthec-dev/zynthec-apps-altsource/main/icons/meine-app.png",
    "category": "utilities"
  }
}
```

## miPet

Die öffentliche Ausgabe erfordert einen eigenen Gemini-API-Schlüssel in den Einstellungen. Die IPA ist unsigniert; SideStore signiert beim Installieren. iCloud benötigt passende Berechtigungen beim Signieren. Datei-Backups funktionieren unabhängig davon.

## Lokal prüfen

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/update_owned_app.py
python3 scripts/check_source.py --remote
```

Nur Python-Standardbibliothek erforderlich. Downloads sind auf 256 MB je IPA begrenzt. Der vollständige Abgleich prüft jedes veröffentlichte IPA-Asset erneut; bei sehr großen Katalogen sollte ein geprüfter Metadaten-Cache ergänzt werden.
