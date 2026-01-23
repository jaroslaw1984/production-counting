import customtkinter
import customtkinter as ctk
import pandas as pd
import tkinter as tk
import math
import warnings
import os
import tempfile
from ..config.db_loader import fetch_available_machines
from datetime import date, timedelta, datetime
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Dict, Any
from pathlib import Path
from project.config.db_loader import fetch_available_machines, fetch_orders_for_machines, normalize_db_df

# stała ścieżka do pliku konfiguracyjnego
BASE_DIR = Path(__file__).resolve().parent.parent
CONFING_PATH = BASE_DIR / "config" / "profile_config.csv"
MACHINE_CONFIG_PATH = BASE_DIR / "config" / "machine_config.csv"
SHIFTS_PER_DAY = 3

# ignore specific pandas warning about SQLAlchemy
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy connectable*")  

# --- INTERFEJS GRAFICZNY (GUI) ---
def run_app():
    app_state: dict[str, Any] = {"df": None, "table_frame": None, "cfg": None, "current_view_df": None} # Słownik do przechowywania stanu aplikacji (np. wczytany DataFrame)

    customtkinter.set_appearance_mode("Dark")  # Tryby: "System" (domyślny), "Dark", "Light"
    customtkinter.set_default_color_theme("dark-blue")  # Motywy: "blue" (domyślny), "green", "dark-blue"
    
    root = customtkinter.CTk()
    root.title("Policz produkcję")
    root.geometry("800x500")

    def center_popup(parent, popup):
        try:
            parent.update_idletasks()
            popup.update_idletasks()
            pw = popup.winfo_width()
            ph = popup.winfo_height()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            x = rx + (rw - pw) // 2
            y = ry + (rh - ph) // 2
            popup.geometry(f"+{x}+{y}")
        except Exception:
            # best-effort centering — nie przerywamy działania aplikacji
            pass

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
    right.grid_rowconfigure(0, weight=0)  # toolbar
    right.grid_rowconfigure(1, weight=1)  # treść (textbox / tabela)
    
    # --- toolbar nad raportem ---
    # report_toolbar = customtkinter.CTkFrame(right, fg_color="transparent")
    # report_toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 6))
    # report_toolbar.grid_columnconfigure(0, weight=1)
    # report_toolbar.grid_remove()  # ukryty na start

    # przycisk drukowania (startowo ukryty)
    # print_btn = customtkinter.CTkButton(report_toolbar, text="Drukuj raport", command=lambda: print_current_report())
    # print_btn.grid(row=0, column=1, sticky="e")
    # print_btn.grid_remove()  # ukryty dopóki nie ma raportu
        
 # 5) Element, który ma się rozciągać (np. Text lub Treeview)
    text = customtkinter.CTkTextbox(right)
    text.grid(row=1, column=0, sticky="nsew")
    text.configure(state="disabled")  # na start zablokowany do edycji

    
    def _set_print_visible(visible: bool) -> None:
        """Pokazuje/ukrywa przycisk druku (używamy place, bo przycisk jest 'pływający')."""
        if visible:
            print_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        else:
            print_btn.place_forget()


    def print_current_report() -> None:
        report_text = app_state.get("last_report_text", "")
        if not report_text or not report_text.strip():
            messagebox.showwarning("Brak raportu", "Nie ma nic do wydrukowania.")
            _set_print_visible(False)
            return

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
                f.write(report_text)
                path = f.name

            os.startfile(path, "print")  # Windows
        except Exception as e:
            messagebox.showerror("Błąd druku", f"Nie udało się uruchomić druku:\n{e}")

        # przycisk drukowania (startowo ukryty) - pływający prawy dół
    print_btn = customtkinter.CTkButton(
        right,
        text="Drukuj raport",
        command=print_current_report,
        width=140
    )
    print_btn.place_forget()  # ukryty na start

    # placeholder (nakładana etykieta wewnątrz Textboxa)
    placeholder_text = "Program do obliczania produkcji \n\nKliknij 'Wczytaj plik', aby załadować dane. \n\n Następnie kliknij 'Przelicz produkcję', aby uzyskać wyniki. \n\n Dopuszczalne formaty plików Excel: .xlsx .xls"
    placeholder_lbl = customtkinter.CTkLabel(text, text=placeholder_text, justify="center", text_color="#888888", font=default_font)
    # umieść placeholder wewnątrz textboxa, wyśrodkowany
    placeholder_lbl.place(in_=text, relx=0.5, rely=0.5, anchor="center")

    # zmienna statusu i etykieta (wyświetlają liczbę wczytanych rekordów lub komunikaty)
    result_var = tk.StringVar(value="")
    status_label = customtkinter.CTkLabel(left, textvariable=result_var, anchor="w")
    status_label.grid(row=4, column=0, pady=(6, 0), sticky="ew")

    # helper: aktualizuje widoczność placeholdera w textboxie
    def _upadate_placeholder_visibility():
        # sprawdź zawartość i pokaż/ukryj placeholder
        content = text.get("1.0", "end-1c")
        if content.strip():
            placeholder_lbl.place_forget()
        else:
            placeholder_lbl.place(in_=text, relx=0.5, rely=0.5, anchor="center")
            
    # funkcja pokazująca popup wyboru maszyn
    def show_machine_select_popup(machines: list[str], on_confirm):
        popup = ctk.CTkToplevel(root)
        popup.title("Wybór maszyn")
        popup.geometry("620x460")
        popup.resizable(False, False)
        center_popup(root, popup)
        popup.grab_set()
        
        df_mc: pd.DataFrame | None = None  # <-- KLUCZOWA LINIA
        
        # wczytaj machine_config (z cache app_state jeśli jest)
        try:
            df_mc = app_state.get("machine_cfg")
            if df_mc is None or df_mc.empty:
                df_mc = load_machine_config()
                app_state["machine_cfg"] = df_mc
        except Exception as e:
            messagebox.showerror("Błąd konfiguracji", f"Nie mogę wczytać machine_config.csv:\n{e}")
            popup.destroy()
            return

        # tu już NA PEWNO jest DataFrame
        if df_mc is None:
            messagebox.showerror("Błąd", "Brak konfiguracji maszyn (df_mc=None).")
            popup.destroy()
            return

        df_mc_df: pd.DataFrame = df_mc

        vars_map: dict[str, tk.BooleanVar] = {}
        pps_vars: dict[str, tk.StringVar] = {}  # pieces per shift (entry)
        default_pps: dict[str, int] = {}

        title = ctk.CTkLabel(
            popup,
            text="Wybierz maszyny do przeliczenia",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title.pack(pady=(12, 8))

        header = ctk.CTkFrame(popup, fg_color="transparent")
        header.pack(fill="x", padx=12)

        ctk.CTkLabel(header, text="Maszyna", width=220, anchor="w").pack(side="left")
        ctk.CTkLabel(header, text="Szt./zmianę", width=120, anchor="w").pack(side="left")

        scroll = ctk.CTkScrollableFrame(popup, width=580, height=280)
        scroll.pack(padx=12, pady=8, fill="both", expand=True)

        # helper: weź default szt./zmianę z machine_config.csv
        def get_pps_for(machine: str) -> int:
            row = df_mc_df.loc[df_mc_df["workplace"].astype("string").str.strip() == str(machine).strip()]
            if row.empty:
                return 0
            return int(row.iloc[0]["count_by_shift"])

        # budujemy listę: checkbox + entry
        for m in machines:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=3)

            var = tk.BooleanVar(value=False)
            vars_map[m] = var

            cb = ctk.CTkCheckBox(row, text=m, variable=var, width=220)
            cb.pack(side="left", padx=(4, 10))

            pps = get_pps_for(m)
            default_pps[m] = pps
            sv = tk.StringVar(value=str(pps))
            pps_vars[m] = sv

            entry = ctk.CTkEntry(row, width=120, textvariable=sv)
            entry.pack(side="left")

            ctk.CTkLabel(row, text="szt./zmianę", text_color="#aaaaaa").pack(side="left", padx=8)

        # --- TOGGLE: Wybierz/Odznacz wszystkie ---
        def _all_selected() -> bool:
            return all(v.get() for v in vars_map.values()) if vars_map else False

        # helper: odśwież napis przycisku
        def _refresh_toggle_btn_text():
            toggle_btn.configure(text="Odznacz wszystkie" if _all_selected() else "Wybierz wszystkie")

        # funkcja toggle wybiera/odznacza wszystkie
        def toggle_select_all():
            if _all_selected():
                for v in vars_map.values():
                    v.set(False)
            else:
                for v in vars_map.values():
                    v.set(True)
            _refresh_toggle_btn_text()

        # gdy user klika pojedyncze checkboxy, aktualizuj napis przycisku
        for v in vars_map.values():
            try:
                v.trace_add("write", lambda *args: _refresh_toggle_btn_text())
            except Exception:
                pass
         
         # helper: parsowanie int z tekstu (lub None)       
        def _parse_int_or_none(s: str):
            s = (s or "").strip().replace(",", ".")
            if s == "":
                return None
            # pozwól wpisać "120" albo "120.0"
            try:
                return int(float(s))
            except Exception:
                return None

        # potwierdzenie wyboru
        def confirm():
            nonlocal df_mc_df
            selected = [m for m, v in vars_map.items() if v.get()]
            if not selected:
                messagebox.showwarning("Brak wyboru", "Zaznacz przynajmniej jedną maszynę.")
                return

            pps_by_machine = {}
            for m in selected:
                val = _parse_int_or_none(pps_vars[m].get())
                if val is None or val <= 0:
                    messagebox.showerror("Błędna wartość", f"Maszyna {m}: szt./zmianę musi być > 0.")
                    return
                pps_by_machine[m] = int(val)

            # 1) sprawdź zmiany szt./zmianę i ewentualnie zapisz do machine_config.csv
            changes = []
            for m, sv in pps_vars.items():
                new_val = _parse_int_or_none(sv.get())
                if new_val is None or new_val < 0:
                    messagebox.showerror("Błędna wartość", f"Maszyna {m}: nieprawidłowa wartość szt./zmianę.")
                    return
                old_val = int(default_pps.get(m, 0))
                if new_val != old_val:
                    changes.append((m, old_val, new_val))

            if changes:
                # pytamy 1 raz zbiorczo (czytelniej niż spam popupami)
                preview = "\n".join([f"{m}: {old} → {new}" for (m, old, new) in changes[:12]])
                if len(changes) > 12:
                    preview += "\n..."

                if messagebox.askyesno(
                    "Zapis do konfiguracji",
                    "Wykryto zmiany szt./zmianę:\n\n"
                    f"{preview}\n\n"
                    "Zapisać do machine_config.csv?"
                ):
                    for m, _, new_val in changes:
                        mask = df_mc_df["workplace"].astype("string").str.strip() == str(m).strip()
                        if mask.any():
                            df_mc_df.loc[mask, "count_by_shift"] = int(new_val)
                        else:
                            # jeśli maszyny nie ma w configu – dopisujemy z zerową prędkością (żeby nie wywaliło)    
                            new_row = pd.DataFrame([{
                                "workplace": str(m).strip(),
                                "speed_m_per_min": 0.0,
                                "count_by_shift": int(new_val),
                            }])

                            df_mc_df = pd.concat([df_mc_df, new_row], ignore_index=True)

                    app_state["machine_cfg"] = df_mc_df
                    save_machine_config(df_mc_df, MACHINE_CONFIG_PATH)
                    
            popup.destroy()
            on_confirm(selected, pps_by_machine)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=12)

        toggle_btn = ctk.CTkButton(btn_frame, text="Wybierz wszystkie", command=toggle_select_all)
        toggle_btn.pack(side="left")

        ctk.CTkButton(btn_frame, text="Anuluj", command=popup.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_frame, text="Przelicz produkcję", command=confirm).pack(side="right")

        _refresh_toggle_btn_text()

    # funkcja budująca raport tekstowy z DB        
    def build_db_report_pieces(
        df: pd.DataFrame,
        selected_machines: list[str],
        pps_by_machine: dict[str, int],
        start_d: date,
        start_shift: int,
        include_weekends: bool,
    ) -> str:
        lines = []
        lines.append("---- Przewidywane zakończenie produkcji --- \n")

        for machine in selected_machines:
            df_one = df[df["workplace"] == machine].copy()
            if df_one.empty:
                lines.append(f"=== {machine} ===")
                lines.append("Brak danych.\n")
                continue

            # soll i gut w sztukach
            soll = pd.to_numeric(df_one["target_value_pcs"], errors="coerce").fillna(0)
            gut = pd.to_numeric(df_one["good_qty_pcs"], errors="coerce").fillna(0)

            remaining = (soll - gut).clip(lower=0)
            total_remaining = float(remaining.sum())

            pps = int(pps_by_machine.get(machine, 0))

            lines.append(f"=== {machine} ===")
            lines.append(f"Pozostało: {total_remaining:.0f} szt.")

            if pps <= 0:
                lines.append("Szt./zmianę: BRAK / 0 (nie da się policzyć zmian)\n")
                continue

            shifts_exact = total_remaining / pps if total_remaining > 0 else 0.0
            shifts_rounded = round_shifts_custom(shifts_exact)

            # koniec produkcji dla tej maszyny
            end_d, end_s = add_shifts(
                start_date=start_d,
                start_shift=start_shift,
                shifts_count=shifts_rounded,
                include_weekends=include_weekends,
            )

            lines.append(f"Szt./zmianę: {pps}")
            lines.append(f"Zmiany (8h): {shifts_exact:.2f} → {shifts_rounded}")
            lines.append(f"Start liczenia: {pl_weekday_name(start_d)} ({start_d.isoformat()}) zmiana {start_shift}")
            lines.append(f"Produkcja będzie trwać do: {pl_weekday_name(end_d)} (zmiana {end_s})\n")

        return "\n".join(lines)
       
    # funkcja przeliczająca produkcję z DB i pokazująca wyniki w textboxie    
    def calculate_from_db(selected_machines, pps_by_machine):
        # 1) parametry czasu (ten sam popup co w Excelu)
        # bierzemy default szt./zmianę z pierwszej zaznaczonej maszyny
        default_pps = int(pps_by_machine.get(selected_machines[0], 0)) if selected_machines else 0

        choice = ask_schedule_popup(root) 
        
        if not choice:
            return  # anulowano

        calendar_mode = choice.get("calendar", "workdays")
        include_weekends = (calendar_mode == "all")
        start_shift = int(choice.get("start_shift", 1))

        start_mode = choice.get("start_mode", "today")
        start_date_str = choice.get("start_date", date.today().isoformat())

        if start_mode == "date":
            try:
                start_d = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Błąd daty", "Podaj datę w formacie YYYY-MM-DD.")
                return
        else:
            start_d = date.today()

        # 2) dane z DB
        df_raw = fetch_orders_for_machines(selected_machines)
        df = normalize_db_df(df_raw)

        # 3) raport
        report = build_db_report_pieces(
            df=df,
            selected_machines=selected_machines,
            pps_by_machine=pps_by_machine,
            start_d=start_d,
            start_shift=start_shift,
            include_weekends=include_weekends,
        )
        show_text_view()  # <- bez argumentów

        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", report)
        text.configure(state="disabled")
        _upadate_placeholder_visibility()

        app_state["last_report_text"] = report
        _set_print_visible(bool(report.strip()))


    # funkcja wczytująca dane maszyn z DB i pokazująca popup wyboru maszyn
    def loading_machine_data(parent):
        try:
            machines = fetch_available_machines()
        except Exception as e:
            messagebox.showerror("DB error", str(e))
            return

        show_machine_select_popup(machines, calculate_from_db)

    
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
    
    # funkcja wyświetlania tylko tekstu w textboxie (ukrywa tabelę, jeśli była)
    def show_text_view():
        tf = app_state.get("table_frame")
        if tf is not None:
            try:
                tf.destroy()
            except Exception:
                pass
        app_state["table_frame"] = None
        
        
    # funkcja wyświetlania DataFrame w tabeli Treeview
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
        tf.grid(row=1, column=0, sticky="nsew")
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


    # licze dni tygodnia z niestandardowym zaokrągleniem
    def pl_weekday_name(d: date) -> str:
        names = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
        return names[d.weekday()]

    def round_shifts_custom(shifts: float) -> int:
        """4.5 -> 4 (w dół), 4.7 -> 5 (w górę)."""
        frac = shifts - math.floor(shifts)
        return math.floor(shifts) if frac < 0.5 else math.ceil(shifts)

    def next_workday(d: date) -> date:
        d += timedelta(days=1)
        while d.weekday() >= 5:  # 5=sob, 6=nd
            d += timedelta(days=1)
        return d

    # dodaje określoną liczbę zmian do daty i zmiany startowej
    def add_shifts(start_date: date, start_shift: int, shifts_count: int, include_weekends: bool) -> tuple[date, int]:
        """
        Zwraca (end_date, end_shift) po wykonaniu shifts_count zmian,
        startując od start_date i start_shift (1..SHIFTS_PER_DAY).
        """
        if shifts_count <= 0:
            return start_date, start_shift

        d = start_date
        s = start_shift

        # koniec jest na shifts_count-tej zmianie, więc przesuwamy slot shifts_count-1 razy
        moves = shifts_count - 1

        for _ in range(moves):
            s += 1
            if s > SHIFTS_PER_DAY:
                s = 1
                if include_weekends:
                    d += timedelta(days=1)
                else:
                    d = next_workday(d)

        return d, s

    # wczytuje konfigurację maszyn
    def load_machine_config() -> pd.DataFrame:
        if not MACHINE_CONFIG_PATH.exists():
            raise FileNotFoundError(f"Plik konfiguracyjny nie istnieje: {MACHINE_CONFIG_PATH}")

        df_mc = pd.read_csv(MACHINE_CONFIG_PATH, sep=";", encoding="utf-8", dtype={"workplace": "string"})
        df_mc.columns = [col.strip().strip('"').rstrip(";") for col in df_mc.columns]
        
        df_mc.columns = df_mc.columns.str.strip()
        if "machine" in df_mc.columns and "workplace" not in df_mc.columns:
            df_mc = df_mc.rename(columns={"machine": "workplace"})


        required = {"workplace", "speed_m_per_min", "count_by_shift"}
        missing = required - set(df_mc.columns)
        if missing:
            raise ValueError(f"Brakujące kolumny w machine_config.csv: {missing}")

        df_mc["workplace"] = df_mc["workplace"].astype("string").str.strip()
        df_mc["speed_m_per_min"] = pd.to_numeric(df_mc["speed_m_per_min"], errors="coerce").fillna(0.0)
        df_mc["count_by_shift"] = pd.to_numeric(df_mc["count_by_shift"], errors="coerce").fillna(0).astype(int)

        # workplace powinno być unikalne
        duplicates = df_mc.duplicated(subset=["workplace"], keep=False)
        if duplicates.any():
            dup_rows = df_mc[duplicates]
            raise ValueError(f"Duplikaty w machine_config.csv (workplace musi być unikalne):\n{dup_rows}")

        return df_mc

    # sprawdz czy plik istnieje i wczytaj konfigurację profili
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
    
    #--- POPUP: wybór trybu przeliczenia produkcji ---
    def ask_calc_mode_popup(parent, workplace: str, default_speed: float, default_pieces_per_shift: int):
        result: Dict[str, Optional[Dict[str, Any]]] = {"value": None}
        
        # dni roboczoe lub weekend /kalendarz
        calendar_var = tk.StringVar(value="workdays")
        start_shift_var = tk.IntVar(value=1) 
        
        #dni tygodnia / kalendarz
        start_mode_var = tk.StringVar(value="today")  # "today" albo "date"
        start_date_var = tk.StringVar(value=date.today().isoformat())
    

        # ustaw wyraźne tło dla popupu (uniezależnienie od motywu)
        win = customtkinter.CTkToplevel(parent, fg_color="#2b2b2b")
        win.title("Parametry przeliczenia produkcji")

        try:
            win.transient(parent)
        except Exception:
            pass
        try:
            win.grab_release()
        except Exception:
            pass
        try:
            win.lift()
            win.attributes("-topmost", True)
        except Exception:
            pass

        customtkinter.CTkLabel(
            win,
            text=f"Stanowisko: {workplace}",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            text_color="#eaeaea",
        ).pack(padx=16, pady=(14, 6), anchor="w")

        mode_var = tk.StringVar(value="shift")  #  aktywny tryb"speed" albo "shift"

        frame = customtkinter.CTkFrame(win)
        frame.pack(fill="both", expand=True, padx=16, pady=10)

        # radio + entry szt./zmianę
        row2 = customtkinter.CTkFrame(frame)
        row2.pack(fill="x", padx=10, pady=6)
                
        # --- wiersze z opcjami ---
        # prędkość
        row1 = customtkinter.CTkFrame(frame)
        row1.pack(fill="x", padx=10, pady=(10, 6))
                
        # odstęp wizualny między sekcjami
        spacer = customtkinter.CTkFrame(frame, height=12, fg_color="transparent")
        spacer.pack(fill="x")

        # radio + entry szt./zmianę
        row_cal = customtkinter.CTkFrame(frame)
        row_cal.pack(fill="x", padx=10, pady=(20, 6))
        
        # radio dni robocze / weekendy
        row_start = customtkinter.CTkFrame(frame)
        row_start.pack(fill="x", padx=10, pady=6)
        
        # radio data startu
        row_startdate = customtkinter.CTkFrame(frame)
        row_startdate.pack(fill="x", padx=10, pady=6)
        
        # --- tryb startu daty ---
        customtkinter.CTkLabel(row_startdate, text="Start liczenia:", text_color="#eaeaea").pack(side="left")

        customtkinter.CTkRadioButton(
            row_startdate, text="od dziś", variable=start_mode_var, value="today", text_color="#eaeaea"
        ).pack(side="left", padx=10)

        customtkinter.CTkRadioButton(
            row_startdate, text="od daty", variable=start_mode_var, value="date", text_color="#eaeaea"
        ).pack(side="left", padx=10)

        start_date_entry = customtkinter.CTkEntry(row_startdate, width=130, textvariable=start_date_var)
        start_date_entry.pack(side="left", padx=10)

        customtkinter.CTkLabel(row_startdate, text="(YYYY-MM-DD)", text_color="#aaaaaa").pack(side="left")        
        
        # --- tryb przeliczenia ---
        customtkinter.CTkRadioButton(
            row2, text="Przelicz produkcję poprzez sztuki na zmianę:",
            variable=mode_var, value="shift", text_color="#eaeaea"
        ).pack(side="left")

        pshift_var = tk.StringVar(value=str(default_pieces_per_shift))
        pshift_entry = customtkinter.CTkEntry(row2, width=120, textvariable=pshift_var)
        pshift_entry.pack(side="left", padx=10)
        customtkinter.CTkLabel(row2, text="szt./zmianę", text_color="#eaeaea").pack(side="left")

        customtkinter.CTkLabel(row_start, text="Start od zmiany:", text_color="#eaeaea").pack(side="left")

        customtkinter.CTkRadioButton(
            row_start, text="1", variable=start_shift_var, value=1, text_color="#eaeaea"
        ).pack(side="left", padx=10)

        customtkinter.CTkRadioButton(
            row_start, text="2", variable=start_shift_var, value=2, text_color="#eaeaea"
        ).pack(side="left", padx=10)

        customtkinter.CTkRadioButton(
            row_start, text="3", variable=start_shift_var, value=3, text_color="#eaeaea"
        ).pack(side="left", padx=10)

        # --- tryb przeliczenia ---
        customtkinter.CTkRadioButton(
            row1, text="Przelicz produkcję poprzez prędkość:",
            variable=mode_var, value="speed", text_color="#eaeaea"
        ).pack(side="left")

        speed_var = tk.StringVar(value=str(default_speed))
        speed_entry = customtkinter.CTkEntry(row1, width=120, textvariable=speed_var)
        speed_entry.pack(side="left", padx=10)
        customtkinter.CTkLabel(row1, text="m/min", text_color="#eaeaea").pack(side="left")


        customtkinter.CTkLabel(row_cal, text="Kalendarz:", text_color="#eaeaea").pack(side="left")

        customtkinter.CTkRadioButton(
            row_cal, text="dni robocze", variable=calendar_var, value="workdays", text_color="#eaeaea"
        ).pack(side="left", padx=10)

        customtkinter.CTkRadioButton(
            row_cal, text="dni robocze + weekendy", variable=calendar_var, value="all", text_color="#eaeaea"
        ).pack(side="left", padx=10)
        
        # helper: parsowanie float z tekstu
        def parse_float(s: str) -> float:
            return float(s.replace(",", ".").strip())

        # --- przyciski OK ---
        def on_ok():
            try:
                if mode_var.get() == "speed":
                    v = parse_float(speed_var.get())
                    if v <= 0:
                        raise ValueError("Prędkość musi być > 0.")
                    result["value"] = {
                        "mode": "speed",
                        "speed_m_per_min": v,
                        "calendar": calendar_var.get(),
                        "start_shift": int(start_shift_var.get()),
                        }
                    result["value"]["start_mode"] = start_mode_var.get()
                    result["value"]["start_date"] = start_date_var.get()
                    result["value"]["start_shift"] = int(start_shift_var.get())
                else:
                    v = int(parse_float(pshift_var.get()))
                    if v <= 0:
                        raise ValueError("Sztuki na zmianę muszą być > 0.")
                    result["value"] = {
                        "mode": "shift",
                        "pieces_per_shift": v,
                        "calendar": calendar_var.get(),
                        "start_shift": int(start_shift_var.get()),
                        }
                    result["value"]["start_mode"] = start_mode_var.get()
                    result["value"]["start_date"] = start_date_var.get()
                    result["value"]["start_shift"] = int(start_shift_var.get())

            except Exception as e:
                messagebox.showerror("Błędna wartość", str(e))
                return
            win.destroy()

        # --- przyciski Anuluj ---
        def on_cancel():
            result["value"] = None
            win.destroy()

        btns = customtkinter.CTkFrame(win, fg_color="#2b2b2b")
        btns.pack(fill="x", padx=16, pady=(0, 14))
        customtkinter.CTkButton(btns, text="Anuluj", command=on_cancel, fg_color="#3a3a3a").pack(side="right")
        customtkinter.CTkButton(btns, text="OK", command=on_ok, fg_color="#3a3a3a").pack(side="right", padx=10)

        # ustaw pozycję na środku rodzica przed blokowaniem okna
        try:
            center_popup(parent, win)
        except Exception:
            pass
        parent.wait_window(win)
        return result["value"]

    # note: fallback `tk` popup removed — use `ask_calc_mode_popup` (CTkToplevel)

    # popup do wyboru dla przycisku "Wczytaj maszyny " dni tygodnia i startu 
    def ask_schedule_popup(parent) -> dict | None:
        popup = ctk.CTkToplevel(parent)
        popup.title("Parametry liczenia (DB)")
        popup.resizable(False, False)
        popup.grab_set()

        result: dict | None = None

        # --- Kalendarz ---
        cal_var = tk.StringVar(value="workdays")  # workdays | all

        cal_frame = ctk.CTkFrame(popup)
        cal_frame.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(cal_frame, text="Kalendarz:", width=120, anchor="w").pack(side="left")
        ctk.CTkRadioButton(cal_frame, text="dni robocze", variable=cal_var, value="workdays").pack(side="left", padx=10)
        ctk.CTkRadioButton(cal_frame, text="dni robocze + weekendy", variable=cal_var, value="all").pack(side="left", padx=10)

        # --- Start od zmiany ---
        shift_var = tk.IntVar(value=1)

        shift_frame = ctk.CTkFrame(popup)
        shift_frame.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(shift_frame, text="Start od zmiany:", width=120, anchor="w").pack(side="left")
        ctk.CTkRadioButton(shift_frame, text="1", variable=shift_var, value=1).pack(side="left", padx=18)
        ctk.CTkRadioButton(shift_frame, text="2", variable=shift_var, value=2).pack(side="left", padx=18)
        ctk.CTkRadioButton(shift_frame, text="3", variable=shift_var, value=3).pack(side="left", padx=18)

        # --- Start liczenia ---
        start_mode_var = tk.StringVar(value="today")  # today | date
        start_date_var = tk.StringVar(value=date.today().isoformat())

        start_frame = ctk.CTkFrame(popup)
        start_frame.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(start_frame, text="Start liczenia:", width=120, anchor="w").pack(side="left")
        ctk.CTkRadioButton(start_frame, text="od dziś", variable=start_mode_var, value="today").pack(side="left", padx=10)
        ctk.CTkRadioButton(start_frame, text="od daty", variable=start_mode_var, value="date").pack(side="left", padx=10)

        date_entry = ctk.CTkEntry(start_frame, width=140, textvariable=start_date_var)
        date_entry.pack(side="left", padx=10)
        ctk.CTkLabel(start_frame, text="(YYYY-MM-DD)", text_color="#aaaaaa").pack(side="left")

        #--- Przycisk OK ---
        def _on_ok():
            nonlocal result
            mode = start_mode_var.get()
            ds = start_date_var.get().strip()

            if mode == "date":
                try:
                    datetime.strptime(ds, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Błąd daty", "Podaj datę w formacie YYYY-MM-DD.")
                    return

            result = {
                "calendar": cal_var.get(),
                "start_shift": int(shift_var.get()),
                "start_mode": mode,
                "start_date": ds,
            }
            popup.destroy()

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(10, 12))

        ctk.CTkButton(btn_frame, text="Anuluj", command=popup.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_frame, text="OK", command=_on_ok).pack(side="right")

        # ustaw okno na środku rodzica przed blokowaniem
        try:
            center_popup(parent, popup)
        except Exception:
            pass

        popup.wait_window()
        return result

    # główna funkcja przeliczania produkcji
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

        workplaces = df_plan["workplace"].dropna().astype("string").str.strip().unique()
        if len(workplaces) != 1:
            messagebox.showerror("Wybór maszyny", f"W danych wykryto wiele maszyn: {list(workplaces)}")
            return

        workplace = workplaces[0]
        row = df_mc.loc[df_mc["workplace"] == workplace]
        if row.empty:
            messagebox.showerror("Brak konfiguracji", f"Nie znaleziono workplace='{workplace}' w machine_config.csv")
            return

        default_speed = float(row.iloc[0]["speed_m_per_min"])
        default_pieces_per_shift = int(row.iloc[0]["count_by_shift"])


        # Use tkinter fallback popup for debugging visibility issues
        choice = ask_calc_mode_popup(root, workplace, default_speed, default_pieces_per_shift)

        if choice is None:
            return  # Anuluj           

        mask = df_mc["workplace"].astype("string").str.strip() == str(workplace).strip()

        if choice["mode"] == "speed":
            new_speed = float(choice["speed_m_per_min"])

            if abs(new_speed - default_speed) > 1e-9:
                if messagebox.askyesno(
                    "Zapis do konfiguracji",
                    f"Zmieniono prędkość dla {workplace}\n"
                    f"Było: {default_speed}\n"
                    f"Jest: {new_speed}\n\n"
                    "Zapisać do machine_config.csv?"
                ):
                    df_mc.loc[mask, "speed_m_per_min"] = new_speed
                    save_machine_config(df_mc, MACHINE_CONFIG_PATH)
                    app_state["machine_cfg"] = df_mc
                    default_speed = new_speed

        elif choice["mode"] == "shift":  # tryb szt./zmianę
            new_pps = int(choice["pieces_per_shift"])

            if new_pps != default_pieces_per_shift:
                if messagebox.askyesno(
                    "Zapis do konfiguracji",
                    f"Zmieniono szt./zmianę dla {workplace}\n"
                    f"Było: {default_pieces_per_shift}\n"
                    f"Jest: {new_pps}\n\n"
                    "Zapisać do machine_config.csv?"
                ):
                    df_mc.loc[mask, "count_by_shift"] = new_pps
                    save_machine_config(df_mc, MACHINE_CONFIG_PATH)
                    app_state["machine_cfg"] = df_mc
                    default_pieces_per_shift = new_pps

        # --- NORMALIZACJA DANYCH ---
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

        # --- METRY (suma długości do biegu) ---
        if "target_value_p" not in df.columns or "unit_p" not in df.columns:
            messagebox.showerror("Błąd danych", "Brak kolumn target_value_p lub unit_p – nie mogę policzyć metrów.")
            return

        # --- METRY (pozostałe do wykonania) ---
        target_p = pd.to_numeric(df["target_value_p"], errors="coerce").fillna(0.0)
        good_p = pd.to_numeric(df.get("good_qty_p", 0), errors="coerce").fillna(0.0)

        unit = df["unit_p"].astype("string").str.strip().str.upper()

        # domyślnie: cały target
        remaining_p = target_p.copy()

        # jeśli zlecenie rozpoczęte → odejmij wykonaną część
        mask_started = good_p > 0
        remaining_p.loc[mask_started] = (target_p - good_p).clip(lower=0.0)

        # tylko metry (P w metrach)
        df["length_m"] = remaining_p.where(unit == "M", 0.0)

        total_m = float(df["length_m"].sum())

        # --- SZTUKI (suma sztuk do wykonania) ---
        pieces = pd.to_numeric(df["target_value_s"], errors="coerce").fillna(0.0)
        total_pieces = float(pieces.sum())


        # zbrojenia: unikalna konfiguracja profile+side
        unique_setups = df[["profile", "side", "setting_time"]].drop_duplicates(subset=["profile", "side"])
        real_setups = unique_setups[unique_setups["setting_time"] > 0]
        total_setting_min = float(real_setups["setting_time"].sum())

        # --- CZAS BIEGU (wg trybu z popupu) ---
        total_run_min = 0.0
        run_mode_line = ""

        if choice["mode"] == "speed":
            speed = float(choice["speed_m_per_min"])
            if speed <= 0:
                messagebox.showwarning("Błąd", "Prędkość musi być > 0.")
                return
            total_run_min = total_m / speed
            run_mode_line = f"Tryb biegu: {speed:.2f} m/min\n"
        else:
            pieces_per_shift = int(choice["pieces_per_shift"])
            if pieces_per_shift <= 0:
                messagebox.showwarning("Błąd", "Sztuki na zmianę muszą być > 0.")
                return
            if total_pieces <= 0:
                messagebox.showwarning("Błąd danych", "Suma sztuk (Docelowa wartość (S)) wynosi 0 – nie mogę policzyć trybu shift.")
                return

            shifts_needed = total_pieces / pieces_per_shift
            total_run_min = shifts_needed * 8.0 * 60.0
            run_mode_line = f"Tryb biegu: {pieces_per_shift} szt./zmianę\n"

        # podsumowanie
        total_min = total_setting_min + total_run_min
        total_h = total_min / 60.0
        shifts = total_h / 8.0
        
        calendar_mode = choice.get("calendar", "workdays")
        include_weekends = (calendar_mode == "all")
        start_shift = int(choice.get("start_shift", 1))

        rounded_shifts = round_shifts_custom(shifts)

        start_shift = int(choice.get("start_shift", 1))
        start_mode = choice.get("start_mode", "today")
        start_date_str = choice.get("start_date", date.today().isoformat())

        if start_mode == "date":
            try:
                start_d = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Błąd daty", "Podaj datę w formacie YYYY-MM-DD.")
                return
        else:
            start_d = date.today()

        end_d, end_s = add_shifts(
            start_date=start_d,
            start_shift=start_shift,
            shifts_count=rounded_shifts,
            include_weekends=include_weekends
)
        
        end_line = f"Produkcja będzie trwać do: {pl_weekday_name(end_d)} (zmiana {end_s})\n"

        result_text = (
            f"Stanowisko:   {workplace}\n"
            f"Pozycje w planie: {len(df)}\n"
            f"Ilość zbrojeń profili: {len(real_setups)}\n"
            f"Suma metrów:  {total_m:.1f} m\n"
            f"Suma sztuk:   {total_pieces:.0f} szt.\n"
            f"{run_mode_line}"
            f"Czas zbrojeń: {total_setting_min:.1f} min\n"
            f"Czas biegu:   {total_run_min:.1f} min\n"
            f"Razem:        {total_min:.1f} min = {total_h:.2f} h\n"
            f"--------------------------------\n"
            f"Zmiany (8h):  {shifts:.2f}\n"
            f"Start liczenia: {pl_weekday_name(start_d)} ({start_d.isoformat()}) zmiana {start_shift}\n"
            f"{end_line}"
        )

        
        configs = real_setups[["profile", "side", "setting_time"]].sort_values(["profile", "side"])

        result_text += "\nKonfiguracja czasów dla zbrojeń:\n" + configs.to_string(index=False)
        
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", result_text)
        text.configure(state="disabled")
        _upadate_placeholder_visibility()
        
        show_text_view()

        # Debug / opcjonalnie podgląd:
        # show_table_from_df(df)
        
     # funkcja zapisu konfiguracji maszyn   
    def save_machine_config(df_mc: pd.DataFrame, path: Path) -> None:
        df_mc.to_csv(path, sep=";", index=False, encoding="utf-8")

    # funkcja wykrywania kolumny strony
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
                df_raw = pd.read_csv(file_path, encoding="utf-8-sig", sep=",", low_memory=False)
            else:
                messagebox.showerror("Błąd", "Nieobsługiwany format pliku. Wybierz .xlsx, .xls lub .csv")
                return

            # 1) czyść nagłówki (strip + normalizacja spacji)
            df_raw.columns = [
                " ".join(str(c).replace("\xa0", " ").strip().split())
                for c in df_raw.columns
            ]
            
            # funkcja pomocnicza do znajdowania kolumny po możliwych nazwach
            def find_col(df_cols, *candidates):
                cols_norm = {str(c).strip(): str(c) for c in df_cols}
                for cand in candidates:
                    # dokładne dopasowanie po strip
                    for k, original in cols_norm.items():
                        if k == cand.strip():
                            return original
                return None
                        
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
            
            good_p_col = find_col(
                df_raw.columns,
                "Ilość dobrej produkcji (P)",
                "Ilość dobrej produkcji(P)",
                "Ilość dobrej produkcji P",
            )
            
            # mapowanie kolumn na podstawie możliwych nazw
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

            # kolumna wykonania jest opcjonalna – jeśli ją znajdziemy, to ją dokładamy
            if good_p_col:
                needed_fixed.insert(3, good_p_col)

            zlecenie_cols = [c for c in df_raw.columns if c.startswith("Zlecenie")]
            if len(zlecenie_cols) < 2:
                raise ValueError("Brakuje drugiej kolumny 'Zlecenie' (tej ze stroną).")

            df = df_raw[needed_fixed + zlecenie_cols].copy()

            # wybierz tę kolumnę Zlecenie*, która jest stroną
            side_col = detect_side_column(df)

            # teraz zostaw tylko potrzebne kolumny + side_col
            df = df[needed_fixed + [side_col]].copy()
            
            # 3) rename kolumn
            rename_map = {
                "Stanowisko robocze": "workplace",
                "Artykuł": "profile",
                "Docelowa wartość (P)": "target_value_p",
                "Jednostka (P)": "unit_p",
                "Docelowa wartość (S)": "target_value_s",
                "Jednostka (S)": "unit_s",
                "Rodzaj zlecenia": "order_type",
                side_col: "side",
            }
            if good_p_col:
                rename_map[good_p_col] = "good_qty_p"

            df = df.rename(columns=rename_map)
            df["good_qty_p"] = pd.to_numeric(df["good_qty_p"], errors="coerce").fillna(0.0)
            
            
            if "good_qty_p" in df.columns:
                df["good_qty_p"] = (
                    df["good_qty_p"]
                    .astype(str)
                    .str.replace("\xa0", "", regex=False)  # twarda spacja
                    .str.replace(" ", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                df["good_qty_p"] = pd.to_numeric(df["good_qty_p"], errors="coerce").fillna(0.0)
            else:
                df["good_qty_p"] = 0.0


            # fallback gdy jednak nie było kolumny wykonania
            if "good_qty_p" not in df.columns:
                df["good_qty_p"] = 0.0

            # 4) czyść dane w kolumnach profile i side
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
        _set_print_visible(False)
        _upadate_placeholder_visibility()



# 6) Przykładowe przyciski w lewym panelu
    download_machine_btn = customtkinter.CTkButton(left, text="Wczytaj maszyny", command=lambda: loading_machine_data(root))
    download_machine_btn.grid(row=0, column=0, pady=(0, 10), sticky="ew")
    load_machine_btn = customtkinter.CTkButton(left, text="Wczytaj plik", command=on_open_file)
    load_machine_btn.grid(row=1, column=0, pady=(0, 10), sticky="ew")
    count_production_btn = customtkinter.CTkButton(left, text="Przelicz produkcję", command=calculate_production)
    count_production_btn.grid(row=2, column=0, pady=(0, 10), sticky="ew")
    clean_btn = customtkinter.CTkButton(left, text="Wyczyść", command=clean_text)
    clean_btn.grid(row=3, column=0, pady=(0, 10), sticky="ew")
    # umieść przycisk przełączania motywu w lewym panelu, aby pasował do pozostałych kontrolek
    # ustaw początkowy tekst zgodnie z aktualnym trybem wyglądu

    toogle_text = "Jasny motyw" if customtkinter.get_appearance_mode() == "Dark" else "Ciemny motyw"
    ch_theme = customtkinter.CTkButton(left, text=toogle_text, command=change)
    ch_theme.grid(row=4, column=0, pady=(20, 10), sticky="ew")

    root.mainloop()