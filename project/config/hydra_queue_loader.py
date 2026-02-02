from __future__ import annotations

from pathlib import Path
import pandas as pd


ORDER_ALIASES = [
    "zlecenie", "nr zlecenia", "zlecenie nr",
    "auftrag", "auftragsnr", "auftragsnummer",
    "order", "order id"
]

GRUNDPROFIL_ALIASES = [
    "grundprofil", "grund profil", "grund-profil",
    "podkład", "podklad", "profil podstawowy"
]


def _norm(text: str) -> str:
    return " ".join(str(text).replace("\xa0", " ").strip().lower().split())


def _contains_any(cell_text: str, aliases: list[str]) -> bool:
    t = _norm(cell_text)
    return any(a in t for a in aliases)


def detect_header_row(xlsx_path: str | Path, max_scan_rows: int = 40) -> int:
    """
    Szuka wiersza nagłówków: musi zawierać coś jak Zlecenie/Auftrag oraz Grundprofil.
    """
    raw = pd.read_excel(xlsx_path, engine="openpyxl", header=None, nrows=max_scan_rows)
    for r in range(len(raw)):
        row = raw.iloc[r].astype(str).tolist()
        has_order = any(_contains_any(c, ORDER_ALIASES) for c in row)
        has_gp = any(_contains_any(c, GRUNDPROFIL_ALIASES) for c in row)
        if has_order and has_gp:
            return r
    raise ValueError("Nie wykryłem wiersza nagłówków (brak Zlecenie/Auftrag lub Grundprofil).")


def find_column(df: pd.DataFrame, aliases: list[str]) -> str:
    """
    Zwraca nazwę kolumny, której nagłówek pasuje do aliasów.
    """
    for col in df.columns:
        if _contains_any(col, aliases):
            return col
    raise ValueError(f"Nie znalazłem kolumny pasującej do aliasów: {aliases}")


def load_hydra_queue(xlsx_path: str | Path) -> pd.DataFrame:
    header_row = detect_header_row(xlsx_path)
    df = pd.read_excel(xlsx_path, engine="openpyxl", header=header_row)

    # normalizacja nazw kolumn
    df.columns = [" ".join(str(c).replace("\xa0", " ").strip().split()) for c in df.columns]

    order_col = find_column(df, ORDER_ALIASES)
    gp_col = find_column(df, GRUNDPROFIL_ALIASES)

    out = df[[order_col, gp_col]].copy()
    out = out.rename(columns={order_col: "order_id", gp_col: "grundprofil"})

    out["order_id"] = out["order_id"].astype("string").str.strip()
    out["grundprofil"] = out["grundprofil"].astype("string").str.strip()

    # tylko sensowne wiersze
    out = out[(out["order_id"] != "") & (out["grundprofil"] != "")]
    return out.reset_index(drop=True)


def cut_from_order(df: pd.DataFrame, start_order_id: str) -> pd.DataFrame:
    start_order_id = str(start_order_id).strip()
    hits = df.index[df["order_id"] == start_order_id].tolist()
    if not hits:
        raise ValueError(f"Nie znaleziono startowego zlecenia: {start_order_id}")
    return df.loc[hits[0]:].reset_index(drop=True)


def build_sequence(df: pd.DataFrame) -> list[str]:
    """
    Zostawiamy kolejność (w tym powroty A...B...A), a tylko duplikaty obok siebie kasujemy.
    """
    seq = df["grundprofil"].tolist()
    out: list[str] = []
    prev = None
    for gp in seq:
        if gp == prev:
            continue
        out.append(gp)
        prev = gp
    return out
