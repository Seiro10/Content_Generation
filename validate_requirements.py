import subprocess
import tempfile
import os
import sys
from pathlib import Path

REQUIREMENTS_FILE = "requirements.txt"

def log(message, kind="info"):
    color = {"info": "\033[94m", "success": "\033[92m", "error": "\033[91m", "reset": "\033[0m"}
    print(f"{color[kind]}{message}{color['reset']}")

def install_package(venv_bin, package):
    try:
        subprocess.check_output(
            [venv_bin / "pip", "install", "--no-cache-dir", package],
            stderr=subprocess.STDOUT,
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.output.decode()

def main():
    if not Path(REQUIREMENTS_FILE).exists():
        log(f"Fichier {REQUIREMENTS_FILE} introuvable.", "error")
        sys.exit(1)

    with open(REQUIREMENTS_FILE) as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        subprocess.run([sys.executable, "-m", "venv", tmp_path], check=True)

        venv_bin = tmp_path / ("Scripts" if os.name == "nt" else "bin")

        subprocess.run([venv_bin / "pip", "install", "--upgrade", "pip"], check=True)

        log(f"🧪 Test de {len(packages)} packages depuis {REQUIREMENTS_FILE}\n")

        failed = []

        for pkg in packages:
            log(f"➡️  {pkg}")
            ok, err = install_package(venv_bin, pkg)
            if ok:
                log(f"   ✅ Installé avec succès", "success")
            else:
                log(f"   ❌ Échec d'installation\n{err}", "error")
                failed.append((pkg, err))

        if failed:
            log("\n🚨 Packages en échec :", "error")
            for pkg, err in failed:
                log(f" - {pkg}", "error")
        else:
            log("\n🎉 Tous les packages ont été installés correctement", "success")

if __name__ == "__main__":
    main()
