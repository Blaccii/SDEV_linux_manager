# Sinners DEV. Artifact Manager

**Sinners DEV. Artifact Manager** ist ein kleines Linux-CLI-Tool für FiveM-/RedM-FXServer.

Das Tool hilft dir dabei, bestehende Server-Installationen zu erkennen, FXServer-Artefakte sauber zu aktualisieren und nach dem Update optional den Cache zu leeren.

Es ist besonders für Pterodactyl-Server gedacht, funktioniert aber auch mit manuellen Linux-Installationen.

Kurz gesagt:

```bash
cd /ur/location/server/mainfolder
sdev adoptserver
sdev install-artifact --clean
```

---

## Warum Linux?

Für FXServer-Hosting ist Linux meistens die bessere Wahl als Windows.

Linux ist auf Servern schlanker, ressourcenschonender und besser automatisierbar. Gerade bei Pterodactyl, Docker, Shell-Scripts und Serververwaltung fühlt sich Linux deutlich natürlicher an.

Windows kann funktionieren, aber für produktive Game-Server ist Linux in den meisten Fällen sauberer, stabiler und einfacher zu warten.

---

## Was kann das Tool?

Sinners DEV. Artifact Manager kann aktuell:

- bestehende FXServer-Installationen automatisch erkennen
- den Artifact-Ordner erkennen, zum Beispiel `alpine`
- den `resources`-Ordner erkennen
- die `server.cfg` erkennen
- den `cache`-Ordner erkennen
- eine lokale `sdev.json` erstellen
- eine lokale `sdev.lock.json` erstellen
- vorhandene Ressourcen übernehmen, ohne sie zu überschreiben
- empfohlene FiveM-Linux-Artefakte von JG Scripts verwenden
- FXServer-Artefakte sicher aktualisieren
- nach einem Artifact-Update fragen, ob der Cache geleert werden soll
- den Cache manuell leeren
- neue Ressourcen aus GitHub, Git oder ZIP-Links hinzufügen
- verwaltete Ressourcen aktualisieren
- Ressourcen auflisten
- Ressourcen aus der Verwaltung entfernen

---

## Was macht das Tool nicht?

Sinners DEV. Artifact Manager ersetzt nicht:

- Pterodactyl
- txAdmin
- dein Server-Panel
- deine Datenbankverwaltung
- Backups

Bei einem Pterodactyl-Server solltest du den Server weiterhin über das Pterodactyl-Panel starten und stoppen.

Das Tool ist für die Verwaltung auf Dateiebene gedacht: Artefakte, Cache, Ressourcen und Konfiguration.

---

## Voraussetzungen

Installiere zuerst die benötigten Pakete:

```bash
sudo apt update
sudo apt install -y python3 git tar unzip
```

Sinners DEV. Artifact Manager benötigt keine extra Python-Libraries.

---

## Installation

ZIP entpacken:

```bash
unzip SDEV_linux_manager_v0_5.zip
cd SDEV_linux_manager_v0_5
```

Dateien ausführbar machen:

```bash
chmod +x sdev.py install.sh
```

Als root installieren:

```bash
install -m 755 sdev.py /usr/local/bin/sdev
```

Oder mit sudo:

```bash
sudo ./install.sh
```

Installation prüfen:

```bash
sdev --version
```

Erwartete Ausgabe:

```text
sdev 0.5.0
```

---

## Schnellstart für bestehende Server

Gehe in deinen Serverordner.

Bei Pterodactyl auf dem Host sieht das meistens so aus:

```bash
cd /var/lib/pterodactyl/volumes/DEINE-SERVER-ID
```

Beispiel:

```bash
cd /var/lib/pterodactyl/volumes/45abe830-c0e3-4604-a97d-32fa3a352652
```

Server erkennen lassen:

```bash
sdev adoptserver
```

Status prüfen:

```bash
sdev status
```

Artifact aktualisieren:

```bash
sdev install-artifact --clean
```

Nach dem Update fragt das Tool:

```text
Clear cache folder 'cache' now? [Y/n]
```

Mit `Enter` oder `Y` wird der Cache geleert.  
Mit `n` wird der Cache nicht geleert.

---

## Typische Pterodactyl-Struktur

Eine typische Installation sieht so aus:

```text
/home/container/
├── alpine/
├── cache/
├── resources/
├── txData/
└── server.cfg
```

Auf dem Host liegt derselbe Inhalt meistens hier:

```text
/var/lib/pterodactyl/volumes/SERVER-ID/
├── alpine/
├── cache/
├── resources/
├── txData/
└── server.cfg
```

Sinners DEV. Artifact Manager erkennt diese Struktur automatisch.

---

## Wichtiger Hinweis zu `alpine`

FiveM-Linux-Artefakte werden normalerweise in einen Ordner namens `alpine` entpackt.

Die meisten Server verwenden daher diese Struktur:

```text
/home/container/
├── alpine/
├── cache/
├── resources/
├── txData/
└── server.cfg
```

Für normale Server musst du hier nichts Besonderes tun.  
Sinners DEV. Artifact Manager erkennt `alpine` automatisch.

Falls dein Server aus irgendeinem Grund einen anderen Artifact-Ordner nutzt, kannst du ihn manuell angeben:

```bash
sdev adoptserver --artifact-folder alpine --force
```

Für die meisten Pterodactyl-Server reicht aber einfach:

```bash
sdev adoptserver
```

---

## Befehl: `adoptserver`

```bash
sdev adoptserver
```

Dieser Befehl scannt den aktuellen Ordner und sucht nach:

- Artifact-Ordner
- `resources`
- `server.cfg`
- `cache`

Danach erstellt das Tool:

```text
sdev.json
sdev.lock.json
```

Beispielausgabe:

```text
SDEV adopted the current server folder.

Detected layout:
  Artifact folder: alpine
  Resources dir:   resources
  Server cfg:      server.cfg
  Cache dir:       cache

Generated config:
  Artifact extract:  .
  Artifact clean:    alpine
  Artifact expected: alpine
  Resources dir:     resources
  Server cfg:        server.cfg
  Cache dir:         cache
  Cache after update:ask

Imported local resources as unmanaged: 13
```

---

## Was passiert mit bestehenden Ressourcen?

Bestehende Ressourcen werden nicht überschrieben.

Wenn du `sdev adoptserver` ausführst, übernimmt das Tool deine vorhandenen Ressourcen nur in die Lockfile.

Sie werden als `local/unmanaged` markiert.

Das bedeutet:

- SDEV kennt die Ressource
- SDEV löscht sie nicht
- SDEV überschreibt sie nicht
- `sdev update` aktualisiert sie nicht

Das ist absichtlich so, damit bestehende Server sicher übernommen werden können.

---

## Artifact-Update

Sinners DEV. Artifact Manager nutzt standardmäßig die empfohlene Linux-Artifact-Version von JG Scripts.

Artifact-Info anzeigen:

```bash
sdev artifact-info
```

Artifact installieren oder aktualisieren:

```bash
sdev install-artifact --clean
```

Dabei wird nur der konfigurierte Artifact-Ordner gelöscht und neu installiert.

Bei einer normalen Pterodactyl-Installation ist das:

```text
alpine/
```

Nicht gelöscht werden:

```text
resources/
txData/
server.cfg
sdev.json
sdev.lock.json
cache/
```

Der Cache wird nur geleert, wenn du die Cache-Frage bestätigst.

---

## Artifact direkt per URL installieren

Du kannst auch einen direkten Artifact-Link verwenden:

```bash
sdev install-artifact "https://runtime.fivem.net/artifacts/fivem/build_proot_linux/master/XXXXX/fx.tar.xz" --clean
```

---

## Cache leeren

Nach einem Artifact-Update fragt das Tool automatisch:

```text
Clear cache folder 'cache' now? [Y/n]
```

Antworten:

```text
Enter   Cache leeren
Y       Cache leeren
n       Cache nicht leeren
```

Cache manuell leeren:

```bash
sdev clear-cache
```

Ohne Nachfrage:

```bash
sdev clear-cache -y
```

---

## Cache-Modus ändern

Standardmäßig fragt Sinners DEV. Artifact Manager nach jedem Artifact-Update.

Nachfragen:

```bash
sdev cache-mode ask
```

Immer automatisch leeren:

```bash
sdev cache-mode always
```

Nie automatisch leeren:

```bash
sdev cache-mode never
```

---

## Ressourcen hinzufügen

Neue Ressourcen können von SDEV verwaltet werden.

GitHub-Beispiel:

```bash
sdev add https://github.com/overextended/ox_lib --name ox_lib
```

Git-Repository:

```bash
sdev add https://github.com/example/example-resource.git --name example-resource
```

ZIP-Datei:

```bash
sdev add https://example.com/resource.zip --name resource-name
```

Neu hinzugefügte Ressourcen werden als `managed` gespeichert.

---

## Ressourcen aktualisieren

```bash
sdev update
```

Dabei gilt:

- verwaltete Git-Ressourcen werden mit `git pull --ff-only` aktualisiert
- verwaltete Archiv-Ressourcen werden neu heruntergeladen
- lokale/unmanaged Ressourcen werden übersprungen

---

## Ressourcen anzeigen

```bash
sdev list
```

Beispiel:

```text
[core]                         local    local
[standalone]                   local    local
ox_lib                         git      managed  https://github.com/overextended/ox_lib.git
```

Bedeutung:

```text
local      bestehende Ressource, wird nicht überschrieben
managed    von SDEV verwaltete Ressource
```

---

## Ressource entfernen

Ressource löschen und aus der Lockfile entfernen:

```bash
sdev remove ox_lib
```

Nur aus der Lockfile entfernen, Ordner behalten:

```bash
sdev remove ox_lib --lock-only
```

---

## Status anzeigen

```bash
sdev status
```

Beispiel:

```text
Sinners DEV. Artifact Manager v0.5.0
Project:             45abe830-c0e3-4604-a97d-32fa3a352652
Profile:             auto
Artifact source:     jgscripts
Artifact version:    30439
Artifact URL:        https://runtime.fivem.net/artifacts/...
Artifact extract:    .
Artifact clean:      alpine
Artifact expected:   alpine
Resources dir:       resources
Server cfg:          server.cfg
Cache dir:           cache
Cache after update:  ask
Resources in lock:   13
```

---

## Artifact auf Probleme prüfen

Ein bestimmtes Artifact prüfen:

```bash
sdev check-artifact 30439
```

---

## Server starten

Es gibt einen Startbefehl:

```bash
sdev run
```

Bei Pterodactyl solltest du diesen Befehl normalerweise nicht nutzen.

Starte deinen Server dort wie gewohnt über das Panel.

`sdev run` ist eher für manuelle Installationen oder Tests gedacht.

---

## Dateien

Nach `sdev adoptserver` entstehen zwei Dateien:

```text
sdev.json
sdev.lock.json
```

### `sdev.json`

Speichert die lokale Server-Konfiguration.

Beispiel:

```json
{
  "name": "45abe830-c0e3-4604-a97d-32fa3a352652",
  "profile": "auto",
  "artifact_source": "jgscripts",
  "artifact_url": "",
  "artifact_extract_dir": ".",
  "artifact_clean_paths": [
    "alpine"
  ],
  "artifact_expected_dir": "alpine",
  "server_dir": ".",
  "resources_dir": "resources",
  "server_cfg": "server.cfg",
  "cache_dir": "cache",
  "clear_cache_after_artifact_update": "ask"
}
```

### `sdev.lock.json`

Speichert:

- bekannte Ressourcen
- verwaltete Ressourcen
- lokale/unmanaged Ressourcen
- zuletzt installiertes Artifact
- Artifact-URL
- Artifact-Version

---

## Sicherheit

Sinners DEV. Artifact Manager löscht keine gefährlichen Pfade wie:

```text
/
.
./
~
```

Clean- und Cache-Pfade müssen innerhalb des aktuellen Serverordners liegen.

Bei einer korrekt erkannten Pterodactyl-Installation löscht ein Artifact-Update nur:

```text
alpine/
```

Nicht gelöscht werden:

```text
resources/
txData/
server.cfg
sdev.json
sdev.lock.json
```

---

## Empfohlener Ablauf für Pterodactyl

Server im Panel stoppen.

Dann auf dem Host:

```bash
cd /var/lib/pterodactyl/volumes/DEINE-SERVER-ID
sdev artifact-info
sdev install-artifact --clean
```

Cache-Frage beantworten.

Danach Server im Panel starten.

---

## Backup-Empfehlung

Vor dem ersten Einsatz ist ein Backup sinnvoll:

```bash
cd /var/lib/pterodactyl/volumes/DEINE-SERVER-ID
tar -czf backup-before-sdev.tar.gz server.cfg resources txData
```

Optional auch den Artifact-Ordner sichern:

```bash
tar -czf alpine-backup.tar.gz alpine
```

---

## Häufige Fehler

### `sdev: command not found`

SDEV ist nicht installiert.

Lösung:

```bash
install -m 755 sdev.py /usr/local/bin/sdev
```

Prüfen:

```bash
which sdev
sdev --version
```

---

### `invalid choice: adoptserver`

Es ist noch eine alte Version installiert.

Lösung:

```bash
install -m 755 sdev.py /usr/local/bin/sdev
```

Danach prüfen:

```bash
sdev --version
```

---

### `sdev.json already exists`

Der Server wurde bereits übernommen.

Neu scannen:

```bash
sdev adoptserver --force
```

---

### Artifact-Ordner wird nicht erkannt

Manuell setzen:

```bash
sdev adoptserver --artifact-folder alpine --force
```

---

### Resources-Ordner wird nicht erkannt

Manuell setzen:

```bash
sdev adoptserver --resources-dir resources --force
```

---

### server.cfg wird nicht erkannt

Manuell setzen:

```bash
sdev adoptserver --server-cfg server.cfg --force
```

---

### Cache-Ordner wird nicht erkannt

Manuell setzen:

```bash
sdev adoptserver --cache-dir cache --force
```

---

## Wichtige Befehle

```bash
sdev --version
sdev --help

sdev adoptserver
sdev adoptserver --force
sdev status

sdev artifact-info
sdev artifact-info --show-broken
sdev check-artifact 30439

sdev install-artifact --clean
sdev install-artifact --clean --clear-cache
sdev install-artifact --clean --no-cache
sdev update-artifact --recommended

sdev clear-cache
sdev clear-cache -y
sdev cache-mode ask
sdev cache-mode always
sdev cache-mode never

sdev add https://github.com/overextended/ox_lib --name ox_lib
sdev list
sdev update
sdev remove ox_lib
sdev remove ox_lib --lock-only

sdev run
```

---

## Aktuelle Grenzen

Sinners DEV. Artifact Manager kann aktuell noch nicht:

- Pterodactyl automatisch starten oder stoppen
- txAdmin verwalten
- Datenbank-Backups erstellen
- komplette Server-Snapshots erstellen
- automatische Rollbacks durchführen
- Ressourcen-Abhängigkeiten automatisch prüfen
- mehrere Serverprofile verwalten

---

## Roadmap-Ideen

Mögliche zukünftige Funktionen:

- `sdev backup`
- `sdev restore`
- `sdev rollback-artifact`
- `sdev snapshot`
- `sdev doctor`
- Rechteprüfung
- automatisches Fixen von Dateibesitzrechten
- Discord-Webhook nach Updates
- Pterodactyl-API-Anbindung
- Update-Historie

---

## Kurzfassung

Server übernehmen:

```bash
sdev adoptserver
```

Artifact aktualisieren:

```bash
sdev install-artifact --clean
```

Cache bestätigen:

```text
Clear cache folder 'cache' now? [Y/n]
```

Status prüfen:

```bash
sdev status
```

Linux-Server, saubere Artifacts, weniger Stress.
