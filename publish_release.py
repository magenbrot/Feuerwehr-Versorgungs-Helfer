"""
Automatisches Release-Skript für Feuerwehr-Versorgungs-Helfer (Client).
Erstellt einen neuen Git-Tag und veröffentlicht ein GitHub-Release mit generiertem Changelog.
"""

import datetime
import subprocess
import sys

# --- Konfiguration ---
REPO_NAME = "magenbrot/Feuerwehr-Versorgungs-Helfer"
MAIN_BRANCH = "main"


def get_latest_tag() -> str | None:
    """Ermittelt den neuesten Git-Tag im Repository."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "--sort=-v:refname"],
            check=True,
            capture_output=True,
            text=True,
            cwd=".",
        )
        tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]
        return tags[0] if tags else None
    except subprocess.CalledProcessError:
        return None


def get_new_version(old_version: str | None) -> str:
    """Berechnet die neue Version basierend auf dem YYYY.MM.PATCH-Schema."""
    current_year_month = datetime.date.today().strftime("%Y.%m")

    if old_version:
        parts = old_version.lstrip("v").split(".")
        if len(parts) == 3:
            old_year_month = f"{parts[0]}.{parts[1]}"
            try:
                old_patch = int(parts[2])
                if old_year_month == current_year_month:
                    return f"{current_year_month}.{old_patch + 1:02d}"
            except ValueError:
                pass

    return f"{current_year_month}.00"


def run_command(command: list[str], description: str) -> None:
    """Führt einen Shell-Befehl aus und gibt Statusmeldungen aus."""
    print(f"\n-> {description}")
    print(f"   Befehl: {' '.join(command)}")

    result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=".")
    print("   [OK]")
    if result.stdout:
        print(f"   Stdout:\n{result.stdout.strip()}")


def main() -> None:
    """Hauptablauf für die Release-Erstellung."""
    try:
        latest_tag = get_latest_tag()
        new_version = get_new_version(latest_tag)
        tag_name = new_version

        print(f"Letzter Tag: {latest_tag} -> Neuer Tag / Version: {new_version}")

        commands = [
            (["git", "tag", tag_name], f"Erstelle Git-Tag {tag_name}"),
            (["git", "push", "origin", tag_name], f"Pushe Tag {tag_name} zu Origin"),
            (
                [
                    "gh",
                    "release",
                    "create",
                    tag_name,
                    f"--repo={REPO_NAME}",
                    f"--title=Feuerwehr-Versorgungs-Helfer {tag_name}",
                    "--generate-notes",
                ],
                "Erstelle GitHub Release mit automatischer Changelog-Generierung",
            ),
        ]

        for cmd, desc in commands:
            run_command(cmd, desc)

        print("\n" + "=" * 50)
        print("Release erfolgreich initiiert!")
        print("Der GitHub-Workflow paketiert nun das Quellcode-ZIP und hängt es an das Release an.")
        print("=" * 50)

    except subprocess.CalledProcessError as err:
        print(f"\nBefehl fehlgeschlagen: {err.stderr}")
        sys.exit(1)
    except Exception as err:  # pylint: disable=broad-except
        print(f"\nEin Fehler ist aufgetreten: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
