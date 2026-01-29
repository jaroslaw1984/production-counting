from __future__ import annotations
import pandas as pd
import pyodbc

PLAN_SERVER = "kronos.sip.local"
PLAN_DB = "Raporty"
PLAN_TABLE = "dbo.tblPlanowanieWorkplaces"

def _pick_driver() -> str:
    drivers = pyodbc.drivers()
    for name in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
        if name in drivers:
            return name
    raise RuntimeError(f"No SQL Server ODBC driver found. Available: {drivers}")

def _connect_plan() -> pyodbc.Connection:
    driver = _pick_driver()
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={PLAN_SERVER};"
        f"DATABASE={PLAN_DB};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def fetch_workplace_config() -> pd.DataFrame:
    sql = f"SELECT workplace, speed_m_per_min, count_by_shift FROM {PLAN_TABLE}"
    with _connect_plan() as conn:
        df = pd.read_sql(sql, conn)
    return df

# ... masz już PLAN_SERVER/PLAN_DB/PLAN_TABLE/_connect_plan()

def insert_missing_workplaces(df_missing: pd.DataFrame) -> None:
    """
    Dopisuje brakujące workplace do tabeli (tylko INSERT).
    df_missing musi mieć kolumny: workplace, speed_m_per_min, count_by_shift
    """
    if df_missing is None or df_missing.empty:
        return

    sql = f"""
        INSERT INTO {PLAN_TABLE} (workplace, speed_m_per_min, count_by_shift)
        VALUES (?, ?, ?)
    """

    rows = []
    for _, r in df_missing.iterrows():
        wp = str(r["workplace"]).strip()
        sp = float(r["speed_m_per_min"]) if pd.notna(r["speed_m_per_min"]) else None
        cb = int(r["count_by_shift"]) if pd.notna(r["count_by_shift"]) else None
        rows.append((wp, sp, cb))

    with _connect_plan() as conn:
        cur = conn.cursor()
        cur.fast_executemany = True
        cur.executemany(sql, rows)
        conn.commit()
        
def update_count_by_shift(workplace: str, count_by_shift: int) -> None:
    sql = f"UPDATE {PLAN_TABLE} SET count_by_shift = ? WHERE workplace = ?"
    with _connect_plan() as conn:
        cur = conn.cursor()
        cur.execute(sql, (int(count_by_shift), str(workplace).strip()))
        conn.commit()

def update_speed(workplace: str, speed_m_per_min: float) -> None:
    sql = f"UPDATE {PLAN_TABLE} SET speed_m_per_min = ? WHERE workplace = ?"
    with _connect_plan() as conn:
        cur = conn.cursor()
        cur.execute(sql, (float(speed_m_per_min), str(workplace).strip()))
        conn.commit()

