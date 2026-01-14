import customtkinter
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from project.Core.data_loader import load_excel
from typing import Optional, Dict, Any
from pathlib import Path
from typing import Any

# stała ścieżka do pliku konfiguracyjnego
BASE_DIR = Path(__file__).resolve().parent.parent
CONFING_PATH = BASE_DIR / "config" / "profile_config.csv"
MACHINE_CONFIG_PATH = BASE_DIR / "config" / "machine_config.csv"

# --- INTERFEJS GRAFICZNY (GUI) ---
def run_app():
    app_state: dict[str, Any] = {"df": None, "table_frame": None, "cfg": None, "current_view_df": None} # Słownik do przechowywania stanu aplikacji (np. wczytany DataFrame)

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

    # funkcja przełączania motywu
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
    
    def show_text_view():
        tf = app_state.get("table_frame")
        if tf is not None:
            try:
                tf.destroy()
            except Exception:
                pass
        app_state["table_frame"] = None
        text.grid(row=0, column=0, sticky="nsew")
        
        
    
    def show_table_from_df(df: pd.DataFrame):
        # 1) schowaj textbox
        # usuń poprzednią, jeśli istnieje
        old_tf = app_state.get("table_frame")
        if old_tf is not None:
            try:
                old_tf.destroy()
            except Exception:
                pass

        # 3) zbuduj nową ramkę + tree
        tf = customtkinter.CTkFrame(right)
        tf.grid(row=0, column=0, sticky="nsew")
        app_state["table_frame"] = tf

        cols = list(map(str, df.columns))
        tree = ttk.Treeview(tf, columns=cols, show="headings")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="w")

        # Uwaga: nie ładuj bez limitu tysięcy wierszy – daj podgląd
        for i, row in enumerate(df.itertuples(index=False, name=None)):
            if i >= 2000:
                break
            tree.insert("", "end", values=row)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)


    def load_machine_config() -> pd.DataFrame:
        if not MACHINE_CONFIG_PATH.exists():
            raise FileNotFoundError(f"Plik konfiguracyjny nie istnieje: {MACHINE_CONFIG_PATH}")

        df_mc = pd.read_csv(MACHINE_CONFIG_PATH, sep=";", encoding="utf-8", dtype={"workplace": "string"})
        df_mc.columns = [col.strip().strip('"').rstrip(";") for col in df_mc.columns]

        required = {"workplace", "speed_m_per_min", "count_by_m"}
        missing = required - set(df_mc.columns)
        if missing:
            raise ValueError(f"Brakujące kolumny w machine_config.csv: {missing}")

        df_mc["workplace"] = df_mc["workplace"].astype("string").str.strip()
        df_mc["speed_m_per_min"] = pd.to_numeric(df_mc["speed_m_per_min"], errors="coerce").fillna(0.0)
        df_mc["count_by_m"] = pd.to_numeric(df_mc["count_by_m"], errors="coerce").fillna(0).astype(int)

        # workplace powinno być unikalne
        duplicates = df_mc.duplicated(subset=["workplace"], keep=False)
        if duplicates.any():
            dup_rows = df_mc[duplicates]
            raise ValueError(f"Duplikaty w machine_config.csv (workplace musi być unikalne):\n{dup_rows}")

        return df_mc

    
    def load_profile_confing() -> pd.DataFrame:
        # spradz czy plik istnieje
        if not CONFING_PATH.exists():
            raise FileNotFoundError(f"Plik konfiguracyjny nie istnieje: {CONFING_PATH}")

        # wczytaj plik konfiguracyjny
        df_cfg = pd.read_csv(
            CONFING_PATH,
            sep=";",
            encoding="utf-8",
            dtype={"profile": "string", "side": "string"},
        )
        # na wszelki wypadek: usunięcie spacji z nazw kolumn
        df_cfg.columns = [col.strip().strip('"').rstrip(";") for col in df_cfg.columns]

        required = {"profile", "side", "setting_time"}
        missing = required - set(df_cfg.columns)
        if missing:
            raise ValueError(f"Brakujące kolumny w pliku konfiguracyjnym: {missing}") 

        # upewnij się, że setting_time jest liczbą
        df_cfg["setting_time"] = pd.to_numeric(df_cfg["setting_time"], errors="coerce").fillna(0).astype(int)

        # kontrola duplikatów (profile+side musi być 1:1)
        duplicates = df_cfg.duplicated(subset=["profile", "side"], keep=False)
        if duplicates.any(): 
            dup_rows = df_cfg[duplicates]
            raise ValueError(f"Duplikaty w pliku konfiguracyjnym (profile+side musi być unikalne):\n{dup_rows}")

        return df_cfg
    
    def ask_calc_mode_popup(parent, workplace: str, default_speed: float, default_m_per_shift: float):
        result: Dict[str, Optional[Dict[str, Any]]] = {"value": None}

        win = customtkinter.CTkToplevel(parent)
        win.title("Parametry przeliczenia produkcji")
        win.geometry("560x240")
        win.transient(parent)
        win.grab_set()

        customtkinter.CTkLabel(
            win,
            text=f"Stanowisko: {workplace}",
            font=customtkinter.CTkFont(size=16, weight="bold")
        ).pack(padx=16, pady=(14, 6), anchor="w")

        mode_var = tk.StringVar(value="speed")

        frame = customtkinter.CTkFrame(win)
        frame.pack(fill="both", expand=True, padx=16, pady=10)

        row1 = customtkinter.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(10, 6))

        customtkinter.CTkRadioButton(
            row1, text="Przelicz produkcję poprzez prędkość:",
            variable=mode_var, value="speed"
        ).pack(side="left")

        speed_var = tk.StringVar(value=str(default_speed))
        speed_entry = customtkinter.CTkEntry(row1, width=120, textvariable=speed_var)
        speed_entry.pack(side="left", padx=10)
        customtkinter.CTkLabel(row1, text="m/min").pack(side="left")

        row2 = customtkinter.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=6)

        customtkinter.CTkRadioButton(
            row2, text="Przelicz produkcję poprzez metry na zmianę:",
            variable=mode_var, value="shift"
        ).pack(side="left")

        mshift_var = tk.StringVar(value=str(default_m_per_shift))
        mshift_entry = customtkinter.CTkEntry(row2, width=120, textvariable=mshift_var)
        mshift_entry.pack(side="left", padx=10)
        customtkinter.CTkLabel(row2, text="m/zmianę").pack(side="left")

        def parse_float(s: str) -> float:
            return float(s.replace(",", ".").strip())

        def on_ok():
            try:
                if mode_var.get() == "speed":
                    v = parse_float(speed_var.get())
                    if v <= 0:
                        raise ValueError("Prędkość musi być > 0.")
                    result["value"] = {"mode": "speed", "speed_m_per_min": v}
                else:
                    v = parse_float(mshift_var.get())
                    if v <= 0:
                        raise ValueError("Metry na zmianę muszą być > 0.")
                    result["value"] = {"mode": "shift", "m_per_shift": v}
            except Exception as e:
                messagebox.showerror("Błędna wartość", str(e))
                return
            win.destroy()

        def on_cancel():
            result["value"] = None
            win.destroy()

        btns = customtkinter.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(0, 14))
        customtkinter.CTkButton(btns, text="Anuluj", command=on_cancel).pack(side="right")
        customtkinter.CTkButton(btns, text="OK", command=on_ok).pack(side="right", padx=10)

        parent.wait_window(win)
        return result["value"]

    
    def calculate_production():
        df_plan = app_state.get("df")
        if df_plan is None or df_plan.empty:
            messagebox.showwarning("Brak danych", "Najpierw wczytaj dane produkcyjne.")
            return

        # config
        try:
            df_cfg = app_state.get("cfg")
            if df_cfg is None or df_cfg.empty:
                df_cfg = load_profile_confing()  # upewnij się, że nazwa funkcji jest poprawna
                app_state["cfg"] = df_cfg
        except Exception as e:
            messagebox.showerror("Błąd wczytywania konfiguracji", str(e))
            return

        df = df_plan.copy()
        
        # --- machine config (speed) ---
        try:
            df_mc = app_state.get("machine_cfg")
            if df_mc is None or df_mc.empty:
                df_mc = load_machine_config()
                app_state["machine_cfg"] = df_mc
        except Exception as e:
            messagebox.showerror("Błąd wczytywania machine_config.csv", str(e))
            return

        workplaces = df["workplace"].dropna().astype("string").str.strip().unique()
        if len(workplaces) != 1:
            messagebox.showerror(
                "Błąd danych",
                f"Plik powinien dotyczyć jednej maszyny, a wykryto: {list(workplaces)}"
            )
            return

        workplace = workplaces[0]
        row = df_mc.loc[df_mc["workplace"] == workplace]
        if row.empty:
            messagebox.showerror("Brak w machine_config", f"Nie znaleziono workplace='{workplace}' w machine_config.csv")
            return

        speed = float(row.iloc[0]["speed_m_per_min"])
        if speed <= 0:
            messagebox.showwarning(
                "Prędkość = 0",
                f"Maszyna '{workplace}' ma speed_m_per_min=0 w configu.\n"
                "Nie mogę policzyć czasu biegu."
            )
            return

        # wymagane kolumny po normalizacji
        required = {"profile", "side"}
        missing_cols = [c for c in required if c not in df.columns]
        if missing_cols:
            messagebox.showerror("Błąd danych", f"Brak kolumn: {missing_cols}\nSprawdź on_open_file().")
            return

        # normalizacja typów (na wszelki wypadek)
        df["profile"] = df["profile"].astype("string").str.strip()
        df["side"] = df["side"].astype("string").str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(4)

        # upewnij się, że config też ma poprawne typy i kolumny
        for col in ("profile", "side", "setting_time"):
            if col not in df_cfg.columns:
                messagebox.showerror("Błąd configu", f"Brak kolumny '{col}' w profile_config.csv")
                return

        df_cfg = df_cfg.copy()
        df_cfg["profile"] = df_cfg["profile"].astype("string").str.strip()
        df_cfg["side"] = df_cfg["side"].astype("string").str.strip().str.zfill(4)
        df_cfg["setting_time"] = pd.to_numeric(df_cfg["setting_time"], errors="coerce")

        # merge
        df = df.merge(df_cfg[["profile", "side", "setting_time"]], on=["profile", "side"], how="left")

        missing = df[df["setting_time"].isna()]
        if not missing.empty:
            missing_pairs = missing[["profile", "side"]].drop_duplicates().head(20)
            messagebox.showerror(
                "Brak w configu",
                "Nie znaleziono setting_time dla:\n"
                + missing_pairs.to_string(index=False)
                + ("\n..." if len(missing_pairs) >= 20 else "")
            )
            return

        # Twoja reguła biznesowa (jeśli 0020 = brak zbrojenia)
        df.loc[df["side"] == "0020", "setting_time"] = 0

        # zbrojenia liczone raz na unikalną konfigurację profile+side
        unique_setups = df[["profile", "side", "setting_time"]].drop_duplicates(subset=["profile", "side"])
        total_setting_min = float(unique_setups["setting_time"].sum())


        # --- czas biegu (opcjonalnie) ---
        # Jeśli metry są w target_value_p i unit_p == 'M'
        AVG_SPEED_M_PER_MIN = speed  # z configu maszyny
        total_run_min = 0.0

        if "target_value_p" in df.columns and "unit_p" in df.columns:
            length_m = pd.to_numeric(df["target_value_p"], errors="coerce").fillna(0)
            unit = df["unit_p"].astype("string").str.strip().str.upper()
            length_m = length_m.where(unit == "M", 0)  # liczymy bieg tylko dla metrów
            df["length_m"] = length_m
            df["run_time_min"] = df["length_m"] / AVG_SPEED_M_PER_MIN
            total_run_min = float(df["run_time_min"].sum())

        unique_setups = df[["profile", "side", "setting_time"]].drop_duplicates(subset=["profile", "side"])
        
        # realne zbrojenia: tylko tam, gdzie setting_time > 0
        real_setups = unique_setups[unique_setups["setting_time"] > 0]
        total_setting_min = float(real_setups["setting_time"].sum())
        
        total_min = total_setting_min + total_run_min
        total_h = total_min / 60.0
        shifts = total_h / 8.0

        result_text = (
            f"Stanowisko:   {workplace}\n"
            f"Pozycje w planie: {len(df)}\n"
            f"Ilość zbrojeń profili: {len(real_setups)}\n"
            f"Prędkość:     {AVG_SPEED_M_PER_MIN:.2f} m/min\n"
            f"Czas zbrojeń: {total_setting_min:.1f} min\n"
            f"Czas biegu:   {total_run_min:.1f} min\n"
            f"Razem:        {total_min:.1f} min = {total_h:.2f} h\n"
            f"Zmiany (8h):   {shifts:.2f}\n"
        )
        
        configs = real_setups[["profile", "side", "setting_time"]].sort_values(["profile", "side"])

        result_text += "\nKonfiguracja czasów dla zbrojeń:\n" + configs.to_string(index=False)
        
        show_text_view()

        print("CALC DONE", total_setting_min, total_run_min)
        
        
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", result_text)
        text.configure(state="disabled")
        _upadate_placeholder_visibility()

        # Debug / opcjonalnie podgląd:
        # show_table_from_df(df)
    
    def detect_side_column(df: pd.DataFrame) -> str:
        """
        Zwraca kolumnę, która zawiera strony 20/21/22/23.
        Jeśli nie znajdzie – rzuca wyjątek (dane wejściowe są błędne).
        """
        allowed = {"0020", "0021", "0022", "0023"}

        for col in df.columns:
            s = (
                df[col]
                .astype("string")
                .str.strip()
                .str.replace(r"\.0$", "", regex=True)
                .str.zfill(4)
            )

            non_empty = s[s != ""]
            if non_empty.empty:
                continue

            if non_empty.isin(allowed).mean() > 0.8:
                return col

        raise ValueError("Nie znaleziono kolumny strony (20/21/22/23).")


    # funkcja obsługi wczytywania pliku
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
            ext = Path(file_path).suffix.lower()

            if ext in (".xlsx", ".xls"):
                df_raw = pd.read_excel(file_path, engine="openpyxl", header=1)
            elif ext == ".csv":
                df_raw = pd.read_csv(file_path, encoding="utf-8", sep=",", low_memory=False)
            else:
                messagebox.showerror("Błąd", "Nieobsługiwany format pliku. Wybierz .xlsx, .xls lub .csv")
                return

            # 1) czyść nagłówki
            df_raw.columns = [str(c).strip() for c in df_raw.columns]

            # 2) wybierz stałe kolumny
            needed_fixed = [
                "Stanowisko robocze",
                "Artykuł",
                "Docelowa wartość (P)",
                "Jednostka (P)",
                "Docelowa wartość (S)",
                "Jednostka (S)",
                "Rodzaj zlecenia",
            ]

            zlecenie_cols = [c for c in df_raw.columns if c.startswith("Zlecenie")]
            if len(zlecenie_cols) < 2:
                raise ValueError("Brakuje drugiej kolumny 'Zlecenie' (tej ze stroną).")

            df = df_raw[needed_fixed + zlecenie_cols].copy()

            # wybierz tę kolumnę Zlecenie*, która jest stroną
            side_col = detect_side_column(df)

            # teraz zostaw tylko potrzebne kolumny + side_col
            df = df[needed_fixed + [side_col]].copy()

            df = df.rename(columns={
                "Stanowisko robocze": "workplace",
                "Artykuł": "profile",
                "Docelowa wartość (P)": "target_value_p",
                "Jednostka (P)": "unit_p",
                "Docelowa wartość (S)": "target_value_s",
                "Jednostka (S)": "unit_s",
                "Rodzaj zlecenia": "order_type",
                side_col: "side",
            })

            df["profile"] = (
                df["profile"]
                .astype("string")
                .str.strip()
                .str.split("-", n=1)
                .str[0]
            )

            app_state["df"] = df  # zapamiętaj

        except Exception as e:
            messagebox.showerror("Błąd wczytywania pliku", str(e))
            return

        # popup + pokazanie w Treeview (jak u Ciebie)
        popup = customtkinter.CTkToplevel(root)
        popup.title("Wczytano dane")
        popup.geometry("480x180")
        popup.transient(root)
        popup.grab_set()

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

        confirm_button = customtkinter.CTkButton(
            popup,
            text="OK",
            command=lambda: (show_table_from_df(df), popup.destroy())
        )
        confirm_button.pack(pady=(6, 12))

        root.wait_window(popup)

        # tekstowy preview
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", df.head(50).to_string(index=False))
        text.configure(state="disabled")
        _upadate_placeholder_visibility()


    # funkcja czyszczenia textboxa
    def clean_text():
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.configure(state="disabled")
        result_var.set("")
        _upadate_placeholder_visibility()

# 6) Przykładowe przyciski w lewym panelu
    load_machine_btn = customtkinter.CTkButton(left, text="Wczytaj plik", command=on_open_file)
    load_machine_btn.grid(row=0, column=0, pady=(0, 10), sticky="ew")
    count_production_btn = customtkinter.CTkButton(left, text="Przelicz produkcję", command=calculate_production)
    count_production_btn.grid(row=1, column=0, pady=(0, 10), sticky="ew")
    clean_btn = customtkinter.CTkButton(left, text="Wyczyść", command=clean_text)
    clean_btn.grid(row=2, column=0, pady=(0, 10), sticky="ew")
    # umieść przycisk przełączania motywu w lewym panelu, aby pasował do pozostałych kontrolek
    # ustaw początkowy tekst zgodnie z aktualnym trybem wyglądu

    toogle_text = "Jasny motyw" if customtkinter.get_appearance_mode() == "Dark" else "Ciemny motyw"
    ch_theme = customtkinter.CTkButton(left, text=toogle_text, command=change)
    ch_theme.grid(row=3, column=0, pady=(20, 10), sticky="ew")

    root.mainloop()