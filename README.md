# zynthec Apps

Öffentliche App-Quelle für **SideStore** und **AltStore Classic**.

In SideStore unter **Sources → +** einfügen:

```text
https://raw.githubusercontent.com/zynthec-dev/zynthec-apps-altsource/main/source.json
```

[In SideStore hinzufügen](sidestore://source?url=https%3A%2F%2Fraw.githubusercontent.com%2Fzynthec-dev%2Fzynthec-apps-altsource%2Fmain%2Fsource.json)

## Apps

- **SideInstaller** von [FrizzleM](https://github.com/FrizzleM/SideInstaller): direkter Download der Original-IPA. Ein Workflow prüft alle sechs Stunden auf das neueste stabile Release. Versionsnummer, Mindest-iOS und Berechtigungen werden aus der Originaldatei gelesen. Community-Eintrag, keine offizielle Quelle des Entwicklers.
- **miPet** von zynthec: öffentliches Release ohne eingebauten API-Schlüssel. Der eigene Gemini-Zugang wird in der App eingerichtet. Datei-Backups funktionieren unabhängig von iCloud; iCloud setzt passende Signierberechtigungen voraus.

## Eigene Apps und Updates hinzufügen

1. Einmalig einen App-Eintrag in `source.json` ergänzen: eindeutige `bundleIdentifier`, Name, `developerName: "zynthec"`, Beschreibung, Icon-URL, `versions: []`, `appPermissions: {}`. Icon unter `icons/` ablegen.
2. Ein GitHub-Release in diesem Repository als Entwurf erstellen und genau eine schlüsselfreie `.ipa` anhängen. Version und Build in der App vor Updates erhöhen.
3. Release veröffentlichen. `Index own app release` übernimmt die IPA-Daten, fügt die neue Version oben ein und erhält andere Apps sowie ältere Versionen.

Für weitere Versionen einer bestehenden App nur Schritte 2–3 wiederholen. Private API-Schlüssel und persönliche Provisioning-Profile gehören nicht in öffentliche IPAs.

SideInstaller-Updates verändern keine eigenen App-Einträge. Workflows lassen sich zusätzlich manuell starten. Falls GitHub geplante Workflows bei längerer Inaktivität deaktiviert, müssen sie unter Actions wieder aktiviert werden.

## Aufbau

- `source.json`: die öffentlich abrufbare Quelle
- `icons/`: App-Icons
- `scripts/`: Metadatenprüfung und Updater (Python-Standardbibliothek)
- `.github/workflows/`: Updates und Veröffentlichung
- `bootstrap/miPet-0.1.0-2.ipa`: geprüfte Erstveröffentlichung; der Bootstrap-Workflow veröffentlicht sie als Release-Asset

[SideStore-Quellen](https://docs.sidestore.io/docs/advanced/app-sources) · [AltSource-Format](https://faq.altstore.io/developers/make-a-source)
