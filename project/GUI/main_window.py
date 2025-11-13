import customtkinter
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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

    default_font = customtkinter.CTkFont(family="Segoe UI", size=18, weight="bold")

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
    text.configure(state="disabled")  # na start zablokowany do edycji

    # placeholder (nakładana etykieta wewnątrz Textboxa)
    placeholder_text = "Program do obliczania produkcji \n\nKliknij 'Wczytaj plik', aby załadować dane. \n\n Następnie kliknij 'Przelicz produkcję', aby uzyskać wyniki. \n\n Dopuszczalne formaty plików Excel: .xlsx .xls"
    placeholder_lbl = customtkinter.CTkLabel(text, text=placeholder_text, justify="center", text_color="#888888", font=default_font)
    # umieść placeholder wewnątrz textboxa, wyśrodkowany
    placeholder_lbl.place(in_=text, relx=0.5, rely=0.5, anchor="center")

    # zmienna statusu i etykieta (wyświetlają liczbę wczytanych rekordów lub komunikaty)
    result_var = tk.StringVar(value="")
    status_label = customtkinter.CTkLabel(left, textvariable=result_var, anchor="w")
    status_label.grid(row=4, column=0, pady=(6, 0), sticky="ew")

    def _upadate_placeholder_visibility():
        # sprawdź zawartość i pokaż/ukryj placeholder
        content = text.get("1.0", "end-1c")
        if content.strip():
            placeholder_lbl.place_forget()
        else:
            placeholder_lbl.place(in_=text, relx=0.5, rely=0.5, anchor="center")

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
            title="Wybierz plik",
            filetypes=[
                ("Excel files", ("*.xlsx", "*.xls")),
                ("CSV files", ("*.csv",)),
                ("All files", ("*.*",)),
            ],
        )
        if not file_path:
            return
        try:
            df = Path(file_path).suffix.lower()
            if df in (".xlsx", ".xls"):
                # wymagane: openpyxl dla xlsx
                df = pd.read_excel(file_path, engine="openpyxl")
            elif df == ".csv":
                 # dopasuj encoding i separator do Twojego pliku
                df = pd.read_csv(file_path, encoding="utf-8", sep=",", low_memory=False)
            else:
                messagebox.showerror("Błąd", "Nieobsługiwany format pliku. Wybierz plik .xlsx, .xls lub .csv")
                return
            app_state["df"] = df

            # ---- nowy popup z informacją o wczytanych rekordach i akcjami ----
            popup = customtkinter.CTkToplevel(root)
            popup.title("Wczytano dane")
            popup.geometry("480x180")
            popup.transient(root)
            popup.grab_set()

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

            msgbox = f"Wczytano {len(df)} rekordów z pliku:\n{Path(file_path).name}"
            label = customtkinter.CTkLabel(popup, text=msgbox, wraplength=440, anchor="center", justify="center")
            label.pack(padx=12, pady=(12, 6), fill="both")

            # helpery do podglądu/kolumn/tabeli
            def show_preview():
                # usuń ewentualną ramkę z tabelą
                tf = app_state.get("table_frame")
                if tf is not None:
                    try:
                        tf.destroy()
                    except Exception:
                        pass
                    app_state["table_frame"] = None
                # przywróć textbox (jeśli ukryty)
                try:
                    text.grid(row=0, column=0, sticky="nsew")
                except Exception:
                    pass
                # wstaw podgląd do textboxa
                text.configure(state="normal")
                text.delete("1.0", "end")
                preview = df.head(50).to_string(index=False)
                text.insert("end", preview)
                text.configure(state="disabled")
                _upadate_placeholder_visibility()

            def show_columns():
                cols = "\n".join(map(str, df.columns))
                cols_popup = customtkinter.CTkToplevel(root)
                cols_popup.title("Kolumny w pliku")
                cols_popup.geometry("360x300")
                cols_popup.transient(root)
                cols_popup.grab_set()
                lbl = customtkinter.CTkLabel(cols_popup, text=cols, anchor="nw", justify="left")
                lbl.pack(fill="both", expand=True, padx=12, pady=12)
                ok = customtkinter.CTkButton(cols_popup, text="Zamknij", command=cols_popup.destroy)
                ok.pack(pady=(0,12))

            def show_table():
                # ukryj textbox
                try:
                    text.grid_forget()
                except Exception:
                    pass
                # stwórz ramkę na tabelę
                tf = customtkinter.CTkFrame(right)
                tf.grid(row=0, column=0, sticky="nsew")
                app_state["table_frame"] = tf
                cols = list(df.columns)
                tree = ttk.Treeview(tf, columns=cols, show="headings")
                vsb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
                hsb = ttk.Scrollbar(tf, orient="horizontal", command=tree.xview)
                tree.configure(yscroll=vsb.set, xscroll=hsb.set)
                for col in cols:
                    tree.heading(col, text=col)
                    tree.column(col, width=120, anchor="w")
                for i, row in enumerate(df.itertuples(index=False, name=None)):
                    if i >= 2000:
                        break
                    tree.insert("", "end", values=row)
                tree.grid(row=0, column=0, sticky="nsew")
                vsb.grid(row=0, column=1, sticky="ns")
                hsb.grid(row=1, column=0, sticky="ew")
                tf.grid_rowconfigure(0, weight=1)
                tf.grid_columnconfigure(0, weight=1)

            # ramka z przyciskami akcji
            btn_frame = customtkinter.CTkFrame(popup)
            btn_frame.pack(padx=12, pady=(6, 6), fill="x")
            p_btn = customtkinter.CTkButton(btn_frame, text="Pokaż podgląd", command=show_preview)
            p_btn.grid(row=0, column=0, padx=6, pady=6)
            c_btn = customtkinter.CTkButton(btn_frame, text="Pokaż kolumny", command=show_columns)
            c_btn.grid(row=0, column=1, padx=6, pady=6)
            t_btn = customtkinter.CTkButton(btn_frame, text="Otwórz w tabeli", command=show_table)
            t_btn.grid(row=0, column=2, padx=6, pady=6)

            confirm_button = customtkinter.CTkButton(popup, text="OK", command=popup.destroy)
            confirm_button.pack(pady=(6, 12))

            root.wait_window(popup)  # czekaj aż okno zostanie zamknięte

            # po zamknięciu popup wstaw domyślny podgląd
            text.configure(state="normal")
            text.delete("1.0", "end")
            preview = df.head(50).to_string(index=False)  # podgląd, nie cały plik
            text.insert("end", preview)
            text.configure(state="disabled")
            _upadate_placeholder_visibility()
        except Exception as e:
            messagebox.showerror("Błąd", f"Błąd podczas wczytywania pliku: {e}")

    def clean_text():
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.configure(state="disabled")
        result_var.set("")
        _upadate_placeholder_visibility()

# 6) Przykładowe przyciski w lewym panelu
    load_machine_btn = customtkinter.CTkButton(left, text="Wczytaj plik", command=on_open_file)
    load_machine_btn.grid(row=0, column=0, pady=(0, 10), sticky="ew")
    count_production_btn = customtkinter.CTkButton(left, text="Przelicz produkcję")
    count_production_btn.grid(row=1, column=0, pady=(0, 10), sticky="ew")
    clean_btn = customtkinter.CTkButton(left, text="Wyczyść", command=clean_text)
    clean_btn.grid(row=2, column=0, pady=(0, 10), sticky="ew")
    # umieść przycisk przełączania motywu w lewym panelu, aby pasował do pozostałych kontrolek
    # ustaw początkowy tekst zgodnie z aktualnym trybem wyglądu

    toogle_text = "Jasny motyw" if customtkinter.get_appearance_mode() == "Dark" else "Ciemny motyw"
    ch_theme = customtkinter.CTkButton(left, text=toogle_text, command=change)
    ch_theme.grid(row=3, column=0, pady=(20, 10), sticky="ew")

    root.mainloop()