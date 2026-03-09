import subprocess
import shutil
import hashlib
import threading
from pathlib import Path

class ReleaseBuilder:
    def __init__(self, version: str, notes: str, log_callback, done_callback):
        self.version = version
        self.notes = notes
        
        # Funkcje zwrotne (callbacks) do komunikacji z GUI
        self.log = log_callback
        self.on_done = done_callback

        # Ścieżki lokalne (skrypt jest w 'deploy', więc wychodzimy poziom wyżej do roota)
        self.base_dir = Path(__file__).resolve().parent.parent
        self.dist_folder = self.base_dir / "dist" / "production-counter"
        
        # Miejsce na tymczasowego ZIPa (zapiszemy go obok głównego folderu dist)
        self.zip_temp_path = self.base_dir / "dist" / f"ProductionCounter_{self.version}"

        # TODO: Ścieżki sieciowe dodamy w kolejnym kroku

    def start(self):
        """Uruchamia cały proces w tle, by nie zamrozić okna programu."""
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self):
        """Główny przepływ logiki wykonywany w tle."""
        try:
            self.log("=== START PROCESU WDRAŻANIA ===")
            
            # Krok 1: Budowanie EXE
            self._build_exe()
            
            # Krok 2: Pakowanie do ZIP
            zip_file = self._pack_to_zip()
            
            # Krok 3: Wyliczenie SHA256
            sha256_hash = self._calculate_sha256(zip_file)
            
            # Krok 4 & 5 (Sieć) dodamy później
            self.log("Test lokalny zakończony pomyślnie. Plik ZIP czeka w folderze dist.")
            
            self.log("=== PROCES ZAKOŃCZONY ===")
            self.on_done(True) # Sukces

        except Exception as e:
            self.log(f"BŁĄD KRYTYCZNY: {e}")
            self.on_done(False) # Porażka

    def _build_exe(self):
        self.log("Krok 1: Kompilacja kodu przez PyInstaller...")
        
        # Twoja dokładna komenda z notatnika rozbita na listę argumentów
        command = [
            "python", "-m", "PyInstaller", 
            "--noconsole", 
            "--onedir", 
            "--clean", 
            "--name", "production-counter", 
            "--icon", "icon.ico",
            "--add-data", "project\\config\\profile_config.csv;project\\config",
            "--add-data", "project\\config\\machine_config.csv;project\\config",
            "--add-data", "project\\templates\\report_template.docx;project\\templates",
            "--add-data", "project\\data\\help_sections.json;project\\data",
            "--add-data", "project\\data\\help_images;project\\data\\help_images",
            "app.py"
        ]
        
        # Uruchamiamy proces w katalogu głównym projektu (cwd=self.base_dir)
        result = subprocess.run(
            command, 
            cwd=str(self.base_dir), 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            # Jeśli PyInstaller wywali błąd, rzucamy wyjątek z logiem błędu
            raise RuntimeError(f"PyInstaller zgłosił błąd:\n{result.stderr}")
            
        self.log("Kompilacja zakończona sukcesem!")

    def _pack_to_zip(self) -> Path:
        self.log("Krok 2: Tworzenie archiwum ZIP...")
        
        if not self.dist_folder.exists():
            raise FileNotFoundError(f"Nie znaleziono folderu do spakowania: {self.dist_folder}")

        # shutil.make_archive automatycznie dodaje rozszerzenie .zip do base_name
        shutil.make_archive(
            base_name=str(self.zip_temp_path),
            format='zip',
            root_dir=str(self.dist_folder)
        )
        
        final_zip_path = Path(f"{self.zip_temp_path}.zip")
        self.log(f"Archiwum gotowe: {final_zip_path.name} ({final_zip_path.stat().st_size // 1024} KB)")
        return final_zip_path

    def _calculate_sha256(self, file_path: Path) -> str:
        self.log("Krok 3: Wyliczanie sumy kontrolnej SHA256...")
        
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            while chunk := f.read(65536):
                sha256_hash.update(chunk)
                
        calculated_hash = sha256_hash.hexdigest()
        self.log(f"Wyliczony hash: {calculated_hash}")
        return calculated_hash