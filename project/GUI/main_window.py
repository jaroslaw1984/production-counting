import customtkinter
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from project.Core.data_loader import load_excel
from pathlib import Path

# --- INTERFEJS GRAFICZNY (GUI) ---
def run_app():
    app_state = {"df": None}  # Słownik do przechowywania stanu aplikacji (np. wczytany DataFrame)
    
    customtkinter.set_appearance_mode("Dark")  # Tryby: "System" (domyślny), "Dark", "Light"
    customtkinter.set_default_color_theme("dark-blue")  # Motywy: "blue" (domyślny), "green", "dark-blue"
    
    root = customtkinter.CTk()
    root.title("Policz produkcję")
    root.geometry("800x500")

# 1) Główna siatka: 2 kolumny (lewy panel i prawa treść)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)

# 2) Lewy panel (np. przyciski/filtry)
    left = customtkinter.CTkFrame(root)
    left.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
    left.grid_columnconfigure(0, weight=1) # tylko góra-dół

# 3) Prawa część (rośnie w obie strony 
    right = customtkinter.CTkFrame(root)
    right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10) # rośnie w obie strony


# 4) Wnętrze prawego panelu też robimy responsywne
    right.grid_columnconfigure(0, weight=1)
    right.grid_rowconfigure(0, weight=1)

# 5) Element, który ma się rozciągać (np. Text lub Treevie)
    text = customtkinter.CTkTextbox(right)
    text.grid(row=0, column=0, sticky="nsew") # wypełnij cały dostępny obszar

    # zmienna statusu i etykieta (wyświetlają liczbę wczytanych rekordów lub komunikaty)
    result_var = tk.StringVar(value="")
    status_label = customtkinter.CTkLabel(left, textvariable=result_var, anchor="w")
    status_label.grid(row=4, column=0, pady=(6, 0), sticky="ew")

    def change():
        if customtkinter.get_appearance_mode() == "Light":
            customtkinter.set_appearance_mode("Dark")
            try:
                ch_theme.configure(text="Jasny motyw")
            except Exception:
                pass
        else:
            customtkinter.set_appearance_mode("Light")
            try:
                ch_theme.configure(text="Ciemny motyw")
            except Exception:
                pass

    def on_open_file():
        file_path = filedialog.askopenfilename(
            title="Wybierz plik Excel",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not file_path:
            return
        try:
            df = load_excel(file_path)
            app_state["df"] = df  # <-- ZAPAMIĘTAJ DF
            
            # ---- nowy popup z informacją o wczytanych rekordach ----
            popup = customtkinter.CTkToplevel(root)
            popup.title("Wczytano dane")
            popup.geometry("420x140")
            popup.transient(root)  # okno podrzędne względem głównego
            popup.grab_set()  # modalne okno

            # wyśrodkuj popup względem root
            root.update_idletasks()
            popup.update_idletasks()
            rw = root.winfo_width()
            rh = root.winfo_height()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            pw = popup.winfo_width()
            ph = popup.winfo_height()
            x = rx + (rw - pw) // 2
            y = ry + (rh - ph) // 2
            popup.geometry(f"+{x}+{y}")

            popup.grab_set()  # modalne okno

            msgbox = f"Wczytano {len(df)} rekordów z pliku:\n{Path(file_path).name}"
            label = customtkinter.CTkLabel(popup, text=msgbox, wraplength=380, anchor="center", justify="center")
            label.pack(padx=16, pady=(16, 8), fill="both")

            confirm_button = customtkinter.CTkButton(popup, text="OK", command=popup.destroy)
            confirm_button.pack(pady=(20, 16))

            root.wait_window(popup)  # czekaj aż okno zostanie zamknięte
            # -------------------------------------------------------   

            text.configure(state="normal")
            text.delete("1.0", "end")
            preview = df.head(50).to_string(index=False)  # podgląd, nie cały plik
            text.insert("end", preview)
            text.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Błąd", f"Błąd podczas wczytywania pliku: {e}")


# 6) Przykładowe przyciski w lewym panelu
    load_machine = customtkinter.CTkButton(left, text="Wczytaj plik", command=on_open_file)
    load_machine.grid(row=0, column=0, pady=(0, 10), sticky="ew")
    count_button = customtkinter.CTkButton(left, text="Przelicz produkcję")
    count_button.grid(row=1, column=0, pady=(0, 10), sticky="ew")
    clean_button = customtkinter.CTkButton(left, text="Wyczyść")
    clean_button.grid(row=2, column=0, pady=(0, 10), sticky="ew")
    # umieść przycisk przełączania motywu w lewym panelu, aby pasował do pozostałych kontrolek
    # ustaw początkowy tekst zgodnie z aktualnym trybem wyglądu

    toogle_text = "Jasny motyw" if customtkinter.get_appearance_mode() == "Dark" else "Ciemny motyw"
    ch_theme = customtkinter.CTkButton(left, text=toogle_text, command=change)
    ch_theme.grid(row=3, column=0, pady=(20, 10), sticky="ew")

# Jeśli chcesz, by przyciski rozszerzały się na szerokość panelu:
    # left.grid_columnconfigure(0, weight=1)

    root.mainloop()