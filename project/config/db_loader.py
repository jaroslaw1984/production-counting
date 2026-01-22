# project/db/db_loader.py
from __future__ import annotations

import pandas as pd
import pyodbc


SERVER = r"sipdbprod\hydms1"
DATABASE = "hydrawlo"
VIEW_FULLNAME = "hydadm.SOP_Abfrage_Auftragsbestand_Sochacki"


def _pick_driver() -> str:
    drivers = pyodbc.drivers()
    for name in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
        if name in drivers:
            return name
    raise RuntimeError(f"No SQL Server ODBC driver found. Available: {drivers}")

driver = _pick_driver()

def _connect() -> pyodbc.Connection:
    # Uwaga: czasem w firmach jest driver 17 albo 18.
    conn_str = (
        f"DRIVER={{{driver}}};"
        r"SERVER=sipdbprod\hydms1;"
        "DATABASE=hydrawlo;"
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
    with _connect() as conn:
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
            eingeplant,
            artikel
        FROM {VIEW_FULLNAME}
        WHERE masch_nr IN ({placeholders})
          AND Vorgang IN ('0020','0021','0023')
          AND a_status IN ('U','V','L')
          AND eingeplant = 'M'
    """

    with _connect() as conn:
        df = pd.read_sql(sql, conn, params=tuple(machines))

    return df


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
    })

    # 2) czyszczenie tekstów
    out["workplace"] = out["workplace"].astype("string").str.strip()
    out["profile"] = out["profile"].astype("string").str.strip()
    out["side"] = out["side"].astype("string").str.strip()
    out["unit_p"] = out["unit_p"].astype("string").str.strip()
    out["status"] = out["status"].astype("string").str.strip()

    # 3) liczby (na wypadek przecinków dziesiętnych)
    for col in ["target_value_p", "good_qty_p", "aus_bas"]:
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

    return out
