import customtkinter
import pandas as pd
from tkinter import ttk
# from project.GUI.widgets import apply_theme

# --- GUI ---
def run_app():
    customtkinter.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
    customtkinter.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"
    
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

    def load_excler_to_treeview():
        # wczytaj excel (pierwszy arkusz)
        df = pd.read_excel(file_path, engine='openpyxl')


# 6) Przykładowe przyciski w lewym panelu
    load_machine = customtkinter.CTkButton(left, text="Wczytaj plik")
    load_machine.grid(row=0, column=0, pady=(0, 10), sticky="ew")
    count_button = customtkinter.CTkButton(left, text="Przelicz produkcję")
    count_button.grid(row=1, column=0, pady=(0, 10), sticky="ew")
    clean_button = customtkinter.CTkButton(left, text="Wyczyść")
    clean_button.grid(row=2, column=0, pady=(0, 10), sticky="ew")
    # place theme toggle button in the left panel so it matches other controls
    # set initial text according to current appearance
    # 
    toogle_text = "Jasny motyw" if customtkinter.get_appearance_mode() == "Dark" else "Ciemny motyw"
    ch_theme = customtkinter.CTkButton(left, text=toogle_text, command=change)
    ch_theme.grid(row=3, column=0, pady=(20, 10), sticky="ew")

# Jeśli chcesz, by przyciski rozszerzały się na szerokość panelu:
    # left.grid_columnconfigure(0, weight=1)

    root.mainloop()