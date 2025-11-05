import pandas as pd

def load_excel(file_path: str) -> pd.DataFrame:
    """
    Wczytuje plik Excel i zwraca dane jako DataFrame pandas.
    
    :param file_path: Ścieżka do pliku Excel
    :return: DataFrame z danymi z Excela
    """
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        return df
    except Exception as e:
        print(f"Błąd podczas wczytywania pliku Excel: {e}")
        return None