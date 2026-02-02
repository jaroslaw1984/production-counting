# project/db/db_loader.py
from __future__ import annotations

import pandas as pd
import pyodbc
from datetime import date


SERVER = r"sipdbprod\hydms1"
DATABASE = "hydrawlo"
VIEW_FULLNAME = "hydadm.SOP_Abfrage_Auftragsbestand_Sochacki"
SAP_SERVER = "kronos.sip.local"
SAP_DATABASE = "Raporty"


def _pick_driver() -> str:
    drivers = pyodbc.drivers()
    for name in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
        if name in drivers:
            return name
    raise RuntimeError(f"No SQL Server ODBC driver found. Available: {drivers}")

# driver = _pick_driver()

def _connect_hydra() -> pyodbc.Connection:
    driver = _pick_driver()  # <- dopiero teraz, na żądanie
    # Uwaga: czasem w firmach jest driver 17 albo 18.
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(conn_str)

def _connect_sap() -> pyodbc.Connection:
    driver = _pick_driver()
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SAP_SERVER};"
        f"DATABASE={SAP_DATABASE};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def fetch_available_machines() -> list[str]:
    sql = f"""
        SELECT DISTINCT masch_nr
        FROM {VIEW_FULLNAME}
        WHERE masch_nr IS NOT NULL AND LTRIM(RTRIM(masch_nr)) <> ''
        ORDER BY masch_nr
    """
    with _connect_hydra() as conn:
        df = pd.read_sql(sql, conn)

    return df["masch_nr"].astype("string").str.strip().dropna().tolist()


def fetch_orders_for_machines(machines: list[str]) -> pd.DataFrame:
    if not machines:
        return pd.DataFrame()

    placeholders = ",".join(["?"] * len(machines))

    # U/L/V: liczymy wszystkie, ale "remaining" wyjdzie poprawnie
    sql = f"""
        SELECT
            masch_nr,
            erranf_dat,
            erranf_zeit,
            Geometrie,
            Vorgang,
            a_status,
            soll_menge_bas,
            gut_bas,
            aus_bas,
            soll_menge_sek,
            gut_sek,
            aus_sek,
            eingeplant,
            artikel
        FROM {VIEW_FULLNAME}
        WHERE masch_nr IN ({placeholders})
          AND Vorgang IN ('0020','0021','0022','0023')
          AND a_status IN ('U','V','L')
          AND eingeplant = 'M'
    """

    with _connect_hydra() as conn:
        df = pd.read_sql(sql, conn, params=tuple(machines))

    return df

def debug_machine_filters(machine: str):
    # wersja Z FILTRAMI (czyli to co robi program)
    df = fetch_orders_for_machines([machine])

    # wersja BEZ filtrów – surowa prawda z DB
    with _connect_hydra() as conn:
        sql = f"""
            SELECT TOP 200
                masch_nr,
                Vorgang,
                a_status,
                eingeplant,
                soll_menge_sek,
                gut_sek
            FROM {VIEW_FULLNAME}
            WHERE masch_nr = ?
            ORDER BY erranf_dat DESC, erranf_zeit DESC
        """
        raw = pd.read_sql(sql, conn, params=(machine,))

# Zwraca DF w formacie "jak do liczenia":
def normalize_db_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Zwraca DF w formacie "jak do liczenia":
    workplace, profile, side, unit_p, target_value_p, good_qty_p, remaining_p, order_type(optional)
    """
    if df.empty:
        return df

    out = df.copy()

    # 1) nazwy kolumn -> format podobny do Excela
    out = out.rename(columns={
        "masch_nr": "workplace",
        "Geometrie": "profile",
        "Vorgang": "side",
        "eingeplant": "unit_p",
        "soll_menge_bas": "target_value_p",
        "gut_bas": "good_qty_p",
        "a_status": "status",
        "artikel": "article",
        "aus_bas": "aus_bas",
        "soll_menge_sek": "target_value_pcs",
        "gut_sek": "good_qty_pcs",
        "aus_sek": "aus_pcs",
    })

    # 2) czyszczenie tekstów
    out["workplace"] = out["workplace"].astype("string").str.strip()
    out["profile"] = out["profile"].astype("string").str.strip()
    out["side"] = out["side"].astype("string").str.strip()
    out["unit_p"] = out["unit_p"].astype("string").str.strip()
    out["status"] = out["status"].astype("string").str.strip()

    # 3) liczby (na wypadek przecinków dziesiętnych)
    for col in ["target_value_p", "good_qty_p", "aus_bas", "target_value_pcs", "good_qty_pcs", "aus_pcs"]:
        if col in out.columns:
            # jeśli przyjdzie jako tekst "58,5" -> zamiana
            out[col] = (
                out[col]
                .astype("string")
                .str.replace(",", ".", regex=False)
            )
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    # 4) remaining: dla U/L liczymy soll - gut; dla V też wyjdzie soll - 0 (OK)
    out["remaining_p"] = (out["target_value_p"] - out["good_qty_p"]).clip(lower=0.0)
    

    # 5) SZTUKI (jeśli dostępne w DB)
    if "target_value_pcs" in out.columns and "good_qty_pcs" in out.columns:
        out["remaining_pcs"] = (out["target_value_pcs"] - out["good_qty_pcs"]).clip(lower=0.0)


    if "soll_menge_sek" in out.columns and "gut_sek" in out.columns:
        out["remaining_pcs"] = (
            out["soll_menge_sek"].astype("string")
            .str.replace(",", ".", regex=False)
        )
        out["remaining_pcs"] = (
            pd.to_numeric(out["remaining_pcs"], errors="coerce").fillna(0)
            - out["good_qty_pcs"]
        ).clip(lower=0)

    return out

def fetch_sap_basic_profiles(linia: str, day: date) -> pd.DataFrame:
    sql = """
        SELECT INDEKS, ILOSC, JM, IL_SZT, LINIA, DATA, [USER]
        FROM dbo.HANA_ZMDRS_RAPORT
        WHERE LINIA = ? AND CAST(DATA as date) = ?
    """
    with _connect_sap() as conn:
        df = pd.read_sql(sql, conn, params=[linia, day])

    # normalizacja ilości (przecinki)
    df["INDEKS"] = df["INDEKS"].astype("string").str.strip()
    df["ILOSC"] = (
        df["ILOSC"].astype("string").str.replace(",", ".", regex=False)
    )
    df["ILOSC"] = pd.to_numeric(df["ILOSC"], errors="coerce").fillna(0.0)

    return df

    
