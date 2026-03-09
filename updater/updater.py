from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
import hashlib
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


# =========================
# Logging
# =========================

def default_log_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    return base / "ProductionCounter" / "logs" / "updater.log"


def log(msg: str, log_path: Path) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        # brak logów nie może ubić aktualizacji
        pass


# =========================
# GUI status window
# =========================

class UpdateWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Production Counter - Aktualizacja")
        self.root.geometry("460x170")
        self.root.resizable(False, False)

        self._center_window()

        self.root.configure(bg="#1f1f1f")
        self.root.attributes("-topmost", True)

        container = tk.Frame(self.root, bg="#1f1f1f", padx=18, pady=18)
        container.pack(fill="both", expand=True)

        self.title_label = tk.Label(
            container,
            text="Trwa aktualizacja programu",
            font=("Segoe UI", 13, "bold"),
            fg="white",
            bg="#1f1f1f",
            anchor="w",
        )
        self.title_label.pack(fill="x", pady=(0, 8))

        self.status_var = tk.StringVar(value="Inicjalizacja...")
        self.status_label = tk.Label(
            container,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            fg="#d9d9d9",
            bg="#1f1f1f",
            justify="left",
            anchor="w",
            wraplength=410,
        )
        self.status_label.pack(fill="x", pady=(0, 12))

        self.progress = ttk.Progressbar(container, mode="indeterminate", length=410)
        self.progress.pack(fill="x")
        self.progress.start(12)

        self.note_label = tk.Label(
            container,
            text="Proszę nie zamykać tego okna.",
            font=("Segoe UI", 9),
            fg="#9aa0a6",
            bg="#1f1f1f",
            anchor="w",
        )
        self.note_label.pack(fill="x", pady=(10, 0))

        # zablokuj ręczne zamknięcie okna
        self.root.protocol("WM_DELETE_WINDOW", self._do_nothing)

        self.refresh()

    def _do_nothing(self) -> None:
        pass

    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = 460
        h = 170
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w // 2) - (w // 2)
        y = (screen_h // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def refresh(self) -> None:
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            pass

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.refresh()

    def show_error(self, text: str) -> None:
        self.progress.stop()
        self.status_var.set(text)
        self.note_label.configure(text="Aktualizacja została przerwana.")
        self.refresh()
        messagebox.showerror("Błąd aktualizacji", text)

    def close(self) -> None:
        try:
            self.progress.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


# =========================
# Process helpers
# =========================

def pid_exists(pid: int) -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"PID eq {pid}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return str(pid) in out
    except Exception:
        return False

def wait_for_pid_exit(pid: int, timeout_sec: int = 120, ui: UpdateWindow | None = None, log_path: Path | None = None) -> bool:
    t0 = time.time()
    while pid_exists(pid):
        if ui is not None:
            ui.set_status("Oczekiwanie na zamknięcie poprzedniej wersji programu...")
        if log_path is not None:
            log("waiting_for_main_app_exit", log_path)

        if time.time() - t0 > timeout_sec:
            return False

        time.sleep(0.5)
        if ui is not None:
            ui.refresh()

    return True


# =========================
# Update helpers
# =========================

def read_latest(latest_json_path: str) -> dict:
    p = Path(latest_json_path)
    return json.loads(p.read_text(encoding="utf-8"))


def copy_zip(src_path: str, dst_path: Path) -> None:
    shutil.copyfile(src_path, dst_path)


def safe_rmtree(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def find_dir_with_exe(root: Path, exe_name: str) -> Path | None:
    for p in root.rglob(exe_name):
        if p.is_file():
            return p.parent
    return None

def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """
    Oblicza hash SHA-256 dla pliku i porównuje go z oczekiwanym.
    Zwraca True jeśli hashe się zgadzają, False w przeciwnym razie.
    """
    if not expected_hash:
        return False  # Brak hasha traktujemy jako błąd weryfikacji

    sha256_hash = hashlib.sha256()
    
    # Otwieramy plik w trybie binarnym ("rb")
    with file_path.open("rb") as f:
        # Czytamy plik paczkami po 64 KB (65536 bajtów) używając operatora morsa (walrus operator)
        while chunk := f.read(65536):
            sha256_hash.update(chunk)
            
    calculated_hash = sha256_hash.hexdigest()
    
    # Porównujemy ignorując wielkość liter, tak dla bezpieczeństwa
    return calculated_hash.lower() == expected_hash.strip().lower()

def retry(action, *, attempts: int = 30, delay: float = 0.5, on_error=None):
    last = None
    for i in range(attempts):
        try:
            return action()
        except PermissionError as e:
            last = e
            if on_error:
                on_error(i + 1, e)
            time.sleep(delay)
    raise last if last else PermissionError("PermissionError (unknown)")


def clear_dir_contents(dst_dir: Path, log_path: Path, ui: UpdateWindow | None = None) -> None:
    for item in dst_dir.iterdir():
        if ui is not None:
            ui.set_status(f"Usuwanie starych plików: {item.name}")

        def _remove_one():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        def _on_err(attempt, e):
            log(f"remove locked attempt={attempt}: {item} | {e}", log_path)

        retry(_remove_one, attempts=40, delay=0.25, on_error=_on_err)


def copy_dir_contents(src_dir: Path, dst_dir: Path, log_path: Path, ui: UpdateWindow | None = None) -> None:
    for item in src_dir.iterdir():
        src = item
        dst = dst_dir / item.name

        if ui is not None:
            ui.set_status(f"Kopiowanie plików: {item.name}")

        def _copy_one():
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        def _on_err(attempt, e):
            log(f"copy locked attempt={attempt}: {src} -> {dst} | {e}", log_path)

        retry(_copy_one, attempts=40, delay=0.25, on_error=_on_err)


def fail(ui: UpdateWindow, log_path: Path, message: str, code: int) -> int:
    log(f"ERROR: {message}", log_path)
    ui.show_error(message)
    return code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True, help="PID of running app")
    ap.add_argument("--latest_json", required=True, help="Path to latest.json (UNC recommended)")
    ap.add_argument("--current_dir", required=True, help="Path to current app folder (onedir)")
    ap.add_argument("--exe_name", required=True, help="Exe file inside app folder, e.g. production-counter.exe")
    args = ap.parse_args()

    ui = UpdateWindow()
    log_path = default_log_path()

    try:
        log("=== updater start ===", log_path)
        log(f"args.pid={args.pid}", log_path)
        log(f"args.latest_json={args.latest_json}", log_path)
        log(f"args.current_dir={args.current_dir}", log_path)
        log(f"args.exe_name={args.exe_name}", log_path)

        current_dir = Path(args.current_dir).resolve()
        log(f"current_dir_resolved={current_dir}", log_path)

        if not current_dir.exists():
            return fail(ui, log_path, f"Nie znaleziono folderu programu:\n{current_dir}", 2)

        # 1) latest.json
        ui.set_status("Sprawdzanie informacji o nowej wersji...")
        try:
            data = read_latest(args.latest_json)
        except Exception as e:
            return fail(ui, log_path, f"Nie udało się odczytać latest.json:\n{type(e).__name__}: {e}", 3)

        zip_path = str(data.get("zip_path", "")).strip()
        version = str(data.get("version", "")).strip()
        
        # NOWE: Pobieramy sumę kontrolną z pliku JSON
        expected_sha256 = str(data.get("sha256", "")).strip()
        
        log(f"latest.version={version}", log_path)
        log(f"latest.zip_path={zip_path}", log_path)
        log(f"latest.sha256={expected_sha256}", log_path)

        if not zip_path or not version:
            return fail(ui, log_path, "Plik latest.json nie zawiera 'zip_path' lub 'version'.", 3)
            
        # NOWE: Walidacja, czy suma kontrolna w ogóle została podana w JSONie
        if not expected_sha256:
            return fail(ui, log_path, "Plik latest.json nie zawiera sumy kontrolnej 'sha256'. Aktualizacja zatrzymana ze względów bezpieczeństwa.", 3)        
        try:
            data = read_latest(args.latest_json)
        except Exception as e:
            return fail(ui, log_path, f"Nie udało się odczytać latest.json:\n{type(e).__name__}: {e}", 3)

        zip_path = str(data.get("zip_path", "")).strip()
        version = str(data.get("version", "")).strip()
        log(f"latest.version={version}", log_path)
        log(f"latest.zip_path={zip_path}", log_path)

        if not zip_path or not version:
            return fail(ui, log_path, "Plik latest.json nie zawiera 'zip_path' lub 'version'.", 3)

        # 2) download zip -> TEMP
        ui.set_status("Pobieranie nowej wersji programu...")
        tmp_root = Path(tempfile.mkdtemp(prefix="pc_update_"))
        zip_local = tmp_root / f"ProductionCounter_{version}.zip"
        log(f"tmp_root={tmp_root}", log_path)
        log(f"zip_local={zip_local}", log_path)

        try:
            copy_zip(zip_path, zip_local)
            log(f"zip_download_ok size={zip_local.stat().st_size}", log_path)
        except Exception as e:
            return fail(ui, log_path, f"Nie udało się pobrać paczki aktualizacji:\n{type(e).__name__}: {e}", 3)

        # ==========================================
        # NOWY KROK 2.5) Weryfikacja SHA256
        # ==========================================
        ui.set_status("Weryfikacja spójności pobranej paczki...")
        if not verify_sha256(zip_local, expected_sha256):
            return fail(ui, log_path, "Błąd weryfikacji sumy kontrolnej SHA256. Plik instalacyjny jest uszkodzony. Aktualizacja została przerwana.", 8)
        
        log("sha256_verification_ok", log_path)
        # ==========================================

        # 3) extract
        ui.set_status("Rozpakowywanie plików aktualizacji...")
        extract_dir = tmp_root / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_local, "r") as z:
                z.extractall(extract_dir)
            log("extract_ok", log_path)
        except Exception as e:
            return fail(ui, log_path, f"Nie udało się rozpakować paczki:\n{type(e).__name__}: {e}", 4)

        new_dir = find_dir_with_exe(extract_dir, args.exe_name)
        log(f"find_dir_with_exe={new_dir}", log_path)
        if not new_dir:
            return fail(ui, log_path, f"Nie znalazłem pliku {args.exe_name} w rozpakowanej paczce.", 4)

        new_dir = new_dir.resolve()
        log(f"new_dir_resolved={new_dir}", log_path)

        # 4) wait app exit
        ui.set_status("Oczekiwanie na zamknięcie programu...")
        ok = wait_for_pid_exit(args.pid, timeout_sec=120, ui=ui, log_path=log_path)
        log(f"wait_for_pid_exit ok={ok} pid_exists_after={pid_exists(args.pid)}", log_path)
        if not ok and pid_exists(args.pid):
            return fail(ui, log_path, "Poprzednia wersja programu nadal działa. Aktualizacja została przerwana.", 7)

        # 5) swap IN PLACE
        try:
            log(f"pre-swap current_dir_exists={current_dir.exists()} is_dir={current_dir.is_dir()}", log_path)
            log(f"pre-swap new_dir_exists={new_dir.exists()} is_dir={new_dir.is_dir()}", log_path)

            time.sleep(0.5)

            ui.set_status("Usuwanie starych plików programu...")
            log("clear_current_dir_start", log_path)
            clear_dir_contents(current_dir, log_path, ui=ui)
            log("clear_current_dir_ok", log_path)

            ui.set_status("Kopiowanie nowej wersji programu...")
            log("copy_new_files_start", log_path)
            copy_dir_contents(new_dir, current_dir, log_path, ui=ui)
            log("copy_new_files_ok", log_path)

            log("swap_ok", log_path)
        except Exception as e:
            return fail(ui, log_path, f"Podmiana plików nie powiodła się:\n{type(e).__name__}: {e}", 5)

        # 6) start new version
        ui.set_status("Uruchamianie nowej wersji programu...")
        exe_path = current_dir / args.exe_name
        log(f"exe_path={exe_path} exists={exe_path.exists()}", log_path)

        if not exe_path.exists():
            return fail(ui, log_path, "Po aktualizacji nie znaleziono pliku EXE programu.", 6)

        try:
            subprocess.Popen([str(exe_path)], cwd=str(current_dir), close_fds=True)
            log("start_ok", log_path)
        except Exception as e:
            return fail(ui, log_path, f"Nie udało się uruchomić nowej wersji:\n{type(e).__name__}: {e}", 6)
        finally:
            try:
                safe_rmtree(tmp_root)
                log("tmp_cleanup_ok", log_path)
            except Exception as e:
                log(f"tmp_cleanup_failed: {type(e).__name__}: {e}", log_path)

        ui.set_status("Aktualizacja zakończona. Uruchamianie programu...")
        time.sleep(1.0)
        ui.close()

        log("=== updater end OK ===", log_path)
        return 0

    except Exception as e:
        log(f"FATAL: {type(e).__name__}: {e}", log_path)
        try:
            ui.show_error(f"Wystąpił nieoczekiwany błąd:\n{type(e).__name__}: {e}")
        except Exception:
            pass
        return 99


if __name__ == "__main__":
    raise SystemExit(main())