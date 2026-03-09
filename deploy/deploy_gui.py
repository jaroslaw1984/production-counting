import customtkinter as ctk
from datetime import datetime
from deploy_logic import ReleaseBuilder

class DeployApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Konfiguracja głównego okna
        self.title("Production Counter - Wdrażanie (Release Builder)")
        self.geometry("650x600")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self._create_widgets()

    def _create_widgets(self):
        # --- NAGŁÓWEK ---
        self.header_label = ctk.CTkLabel(
            self, 
            text="Kreator Publikacji", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        )
        self.header_label.pack(pady=(20, 10))

        # --- SEKCJA: WERSJA ---
        self.version_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.version_frame.pack(fill="x", padx=40, pady=(10, 5))
        
        self.version_label = ctk.CTkLabel(
            self.version_frame, 
            text="Nowa wersja (np. 2.2.3):", 
            font=ctk.CTkFont(family="Segoe UI", size=14)
        )
        self.version_label.pack(side="left", padx=(0, 10))
        
        self.version_entry = ctk.CTkEntry(
            self.version_frame, 
            width=150,
            placeholder_text="Wpisz wersję..."
        )
        self.version_entry.pack(side="left")

        # --- SEKCJA: NOTATKI ---
        self.notes_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.notes_frame.pack(fill="x", padx=40, pady=(10, 5))
        
        self.notes_label = ctk.CTkLabel(
            self.notes_frame, 
            text="Opis zmian (Release notes):", 
            font=ctk.CTkFont(family="Segoe UI", size=14)
        )
        self.notes_label.pack(anchor="w", pady=(0, 5))
        
        self.notes_textbox = ctk.CTkTextbox(
            self.notes_frame, 
            height=80,
            activate_scrollbars=True
        )
        self.notes_textbox.pack(fill="x")

        # --- SEKCJA: PRZYCISK AKCJI ---
        self.deploy_btn = ctk.CTkButton(
            self, 
            text="Zbuduj i opublikuj", 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            height=45,
            command=self.start_deployment
        )
        self.deploy_btn.pack(fill="x", padx=40, pady=(20, 15))

        # --- SEKCJA: KONSOLA LOGÓW ---
        self.console_label = ctk.CTkLabel(
            self, 
            text="Status operacji:", 
            font=ctk.CTkFont(family="Segoe UI", size=14)
        )
        self.console_label.pack(anchor="w", padx=40)

        self.console_textbox = ctk.CTkTextbox(
            self, 
            height=150, 
            fg_color="#1e1e1e", 
            text_color="#d4d4d4",
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.console_textbox.pack(fill="both", expand=True, padx=40, pady=(5, 20))
        # Blokujemy edycję przez użytkownika
        self.console_textbox.configure(state="disabled")

    # --- METODY POMOCNICZE ---
    def log_message(self, message: str):
        """Dodaje nową linię do konsoli w GUI."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}\n"
        
        self.console_textbox.configure(state="normal")
        self.console_textbox.insert("end", formatted_msg)
        self.console_textbox.see("end") # Automatyczny scroll w dół
        self.console_textbox.configure(state="disabled")
        
        # Wymuszenie odświeżenia widoku
        self.update_idletasks()

    def start_deployment(self):
        version = self.version_entry.get().strip()
        notes = self.notes_textbox.get("1.0", "end").strip()

        if not version:
            self.log_message("BŁĄD: Podaj numer wersji przed publikacją!")
            return

        self.log_message(f"Rozpoczynam przygotowania wersji: {version}")
        self.deploy_btn.configure(state="disabled", text="Przetwarzanie w toku...")

        def on_process_done(success: bool):
            """Funkcja wywoływana, gdy logika skończy pracę."""
            # Przywracamy przycisk (z użyciem after, by wrócić do wątku GUI)
            self.after(0, lambda: self.deploy_btn.configure(state="normal", text="Zbuduj i opublikuj"))
            if success:
                self.after(0, lambda: self.version_entry.delete(0, 'end'))

        # Tworzymy i uruchamiamy logikę
        builder = ReleaseBuilder(
            version=version,
            notes=notes,
            log_callback=self.log_message,
            done_callback=on_process_done
        )
        builder.start()


if __name__ == "__main__":
    app = DeployApp()
    app.mainloop()