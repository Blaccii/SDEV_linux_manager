# Sinners DEV. Artifact Manager

**Sinners DEV. Artifact Manager** is a small Linux CLI tool for FiveM/RedM FXServer.

The tool helps you detect existing server installations, update FXServer artifacts safely, and optionally clear the cache after an update.

It is mainly designed for Pterodactyl servers, but it also works with manual Linux installations.

In short:

```bash
sdev adoptserver
sdev install-artifact --clean
```

---

## Important disclaimer

Always create a backup before using this tool on a live server.

Even though Sinners DEV. Artifact Manager is designed to update artifacts safely, every server setup is different. Wrong paths, custom folder structures, permission issues, interrupted downloads, or manual changes can always cause problems.

Before your first use, and before every important artifact update, back up at least:

```text
server.cfg
resources/
txData/
```

If possible, also back up your current artifact folder:

```text
alpine/
```

You are responsible for your own server files. Never run artifact updates on a production server without a working backup.

---

## Why Linux?

For FXServer hosting, Linux is usually the better choice than Windows.

Linux is lighter, more efficient, and much easier to automate on servers. Especially when working with Pterodactyl, Docker, shell scripts, and server maintenance, Linux feels much more natural.

Windows can work, but for production game servers Linux is usually cleaner, more stable, and easier to maintain.

---

## What can this tool do?

Sinners DEV. Artifact Manager can currently:

- automatically detect existing FXServer installations
- detect the artifact folder, usually `alpine`
- detect the `resources` folder
- detect the `server.cfg`
- detect the `cache` folder
- create a local `sdev.json`
- create a local `sdev.lock.json`
- import existing resources without overwriting them
- use the recommended FiveM Linux artifact from JG Scripts
- safely update FXServer artifacts
- ask whether the cache should be cleared after an artifact update
- clear the cache manually
- add new resources from GitHub, Git, or ZIP links
- update managed resources
- list resources
- remove resources from management

---

## What does this tool not do?

Sinners DEV. Artifact Manager does not replace:

- Pterodactyl
- txAdmin
- your server panel
- your database management
- backups

If you use Pterodactyl, you should still start and stop your server through the Pterodactyl panel.

This tool is meant for file-level management: artifacts, cache, resources, and configuration.

---

## Requirements

Install the required packages first:

```bash
sudo apt update
sudo apt install -y python3 git tar unzip
```

Sinners DEV. Artifact Manager does not require any extra Python libraries.

---

## Installation

Extract the ZIP file:

```bash
unzip SDEV_linux_manager_v0_5.zip
cd SDEV_linux_manager_v0_5
```

Make the files executable:

```bash
chmod +x sdev.py install.sh
```

Install as root:

```bash
install -m 755 sdev.py /usr/local/bin/sdev
```

Or with sudo:

```bash
sudo ./install.sh
```

Check the installation:

```bash
sdev --version
```

Expected output:

```text
sdev 0.5.0
```

---

## Quick start for existing servers

Go into your server folder.

On a Pterodactyl host, this usually looks like this:

```bash
cd /var/lib/pterodactyl/volumes/YOUR-SERVER-ID
```

Example:

```bash
cd /var/lib/pterodactyl/volumes/45abe830-c0e3-4604-a97d-32fa3a352652
```

Let the tool detect the server:

```bash
sdev adoptserver
```

Check the status:

```bash
sdev status
```

Update the artifact:

```bash
sdev install-artifact --clean
```

After the update, the tool asks:

```text
Clear cache folder 'cache' now? [Y/n]
```

Press `Enter` or `Y` to clear the cache.  
Press `n` to skip cache clearing.

---

## Typical Pterodactyl structure

A typical installation looks like this:

```text
/home/container/
├── alpine/
├── cache/
├── resources/
├── txData/
└── server.cfg
```

On the host system, the same content is usually located here:

```text
/var/lib/pterodactyl/volumes/SERVER-ID/
├── alpine/
├── cache/
├── resources/
├── txData/
└── server.cfg
```

Sinners DEV. Artifact Manager detects this structure automatically.

---

## Important note about `alpine`

FiveM Linux artifacts are usually extracted into a folder named `alpine`.

Most servers therefore use this structure:

```text
/home/container/
├── alpine/
├── cache/
├── resources/
├── txData/
└── server.cfg
```

For normal servers, you do not need to do anything special.  
Sinners DEV. Artifact Manager detects `alpine` automatically.

If your server uses a different artifact folder for some reason, you can set it manually:

```bash
sdev adoptserver --artifact-folder alpine --force
```

For most Pterodactyl servers, this is enough:

```bash
sdev adoptserver
```

---

## Command: `adoptserver`

```bash
sdev adoptserver
```

This command scans the current folder and looks for:

- artifact folder
- `resources`
- `server.cfg`
- `cache`

After that, the tool creates:

```text
sdev.json
sdev.lock.json
```

Example output:

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

## What happens to existing resources?

Existing resources are not overwritten.

When you run:

```bash
sdev adoptserver
```

the tool only imports your existing resources into the lockfile.

They are marked as `local/unmanaged`.

That means:

- SDEV knows the resource exists
- SDEV does not delete it
- SDEV does not overwrite it
- `sdev update` does not update it

This is intentional, so existing servers can be adopted safely.

---

## Artifact updates

Sinners DEV. Artifact Manager uses the recommended Linux artifact from JG Scripts by default.

Show artifact information:

```bash
sdev artifact-info
```

Install or update the artifact:

```bash
sdev install-artifact --clean
```

Only the configured artifact folder is deleted and reinstalled.

For a normal Pterodactyl installation, that is:

```text
alpine/
```

These files and folders are not deleted:

```text
resources/
txData/
server.cfg
sdev.json
sdev.lock.json
cache/
```

The cache is only cleared if you confirm the cache prompt.

---

## Install artifact from a direct URL

You can also use a direct artifact link:

```bash
sdev install-artifact "https://runtime.fivem.net/artifacts/fivem/build_proot_linux/master/XXXXX/fx.tar.xz" --clean
```

---

## Clear cache

After an artifact update, the tool asks automatically:

```text
Clear cache folder 'cache' now? [Y/n]
```

Answers:

```text
Enter   clear cache
Y       clear cache
n       do not clear cache
```

Clear cache manually:

```bash
sdev clear-cache
```

Without confirmation:

```bash
sdev clear-cache -y
```

---

## Change cache mode

By default, Sinners DEV. Artifact Manager asks after every artifact update.

Ask after updates:

```bash
sdev cache-mode ask
```

Always clear automatically:

```bash
sdev cache-mode always
```

Never clear automatically:

```bash
sdev cache-mode never
```

---

## Add resources

New resources can be managed by SDEV.

GitHub example:

```bash
sdev add https://github.com/overextended/ox_lib --name ox_lib
```

Git repository:

```bash
sdev add https://github.com/example/example-resource.git --name example-resource
```

ZIP file:

```bash
sdev add https://example.com/resource.zip --name resource-name
```

Newly added resources are saved as `managed`.

---

## Update resources

```bash
sdev update
```

Rules:

- managed Git resources are updated with `git pull --ff-only`
- managed archive resources are downloaded again
- local/unmanaged resources are skipped

---

## List resources

```bash
sdev list
```

Example:

```text
[core]                         local    local
[standalone]                   local    local
ox_lib                         git      managed  https://github.com/overextended/ox_lib.git
```

Meaning:

```text
local      existing resource, will not be overwritten
managed    resource managed by SDEV
```

---

## Remove a resource

Delete the resource and remove it from the lockfile:

```bash
sdev remove ox_lib
```

Only remove it from the lockfile, but keep the folder:

```bash
sdev remove ox_lib --lock-only
```

---

## Show status

```bash
sdev status
```

Example:

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

## Check an artifact for known issues

Check a specific artifact:

```bash
sdev check-artifact 30439
```

---

## Start the server

There is a run command:

```bash
sdev run
```

For Pterodactyl installations, you normally should not use this command.

Start your server through the Pterodactyl panel as usual.

`sdev run` is mainly useful for manual installations or testing.

---

## Files

After running:

```bash
sdev adoptserver
```

two files are created:

```text
sdev.json
sdev.lock.json
```

### `sdev.json`

Stores the local server configuration.

Example:

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

Stores:

- known resources
- managed resources
- local/unmanaged resources
- last installed artifact
- artifact URL
- artifact version

---

## Safety

Sinners DEV. Artifact Manager refuses dangerous delete paths like:

```text
/
.
./
~
```

Clean and cache paths must be inside the current server folder.

For a correctly detected Pterodactyl installation, an artifact update only deletes:

```text
alpine/
```

These files and folders are not deleted:

```text
resources/
txData/
server.cfg
sdev.json
sdev.lock.json
```

---

## Recommended Pterodactyl workflow

Stop the server in the panel first.

Then run this on the host:

```bash
cd /var/lib/pterodactyl/volumes/YOUR-SERVER-ID
sdev artifact-info
sdev install-artifact --clean
```

Answer the cache prompt.

Then start the server again in the panel.

---

## Backup recommendation

Before the first use, creating a backup is recommended:

```bash
cd /var/lib/pterodactyl/volumes/YOUR-SERVER-ID
tar -czf backup-before-sdev.tar.gz server.cfg resources txData
```

Optionally back up the artifact folder too:

```bash
tar -czf alpine-backup.tar.gz alpine
```

---

## Common errors

### `sdev: command not found`

SDEV is not installed.

Fix:

```bash
install -m 755 sdev.py /usr/local/bin/sdev
```

Check:

```bash
which sdev
sdev --version
```

---

### `invalid choice: adoptserver`

An old version is still installed.

Fix:

```bash
install -m 755 sdev.py /usr/local/bin/sdev
```

Then check:

```bash
sdev --version
```

---

### `sdev.json already exists`

The server has already been adopted.

Scan again:

```bash
sdev adoptserver --force
```

---

### Artifact folder is not detected

Set it manually:

```bash
sdev adoptserver --artifact-folder alpine --force
```

---

### Resources folder is not detected

Set it manually:

```bash
sdev adoptserver --resources-dir resources --force
```

---

### server.cfg is not detected

Set it manually:

```bash
sdev adoptserver --server-cfg server.cfg --force
```

---

### Cache folder is not detected

Set it manually:

```bash
sdev adoptserver --cache-dir cache --force
```

---

## Important commands

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

## Current limitations

Sinners DEV. Artifact Manager currently cannot:

- start or stop Pterodactyl servers automatically
- manage txAdmin
- create database backups
- create full server snapshots
- perform automatic rollbacks
- automatically check resource dependencies
- manage multiple server profiles

---

## Roadmap ideas

Possible future features:

- `sdev backup`
- `sdev restore`
- `sdev rollback-artifact`
- `sdev snapshot`
- `sdev doctor`
- permission checks
- automatic ownership fixes
- Discord webhook after updates
- Pterodactyl API integration
- update history

---

## Short version

Adopt a server:

```bash
sdev adoptserver
```

Update artifact:

```bash
sdev install-artifact --clean
```

Confirm cache clearing:

```text
Clear cache folder 'cache' now? [Y/n]
```

Check status:

```bash
sdev status
```

Linux servers, clean artifacts, less stress.
