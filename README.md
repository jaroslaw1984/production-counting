# Production Counting

Aplikacja desktopowa (CustomTkinter) do przeliczania produkcji na zmiany
oraz generowania raportów zapotrzebowania materiałowego (SAP),
używana w planowaniu produkcji profili okiennych.

## Główne funkcje
- wczytywanie konfiguracji maszyn (DB + CSV)
- przeliczanie produkcji na zmiany (szt./zmianę lub prędkość)
- uwzględnianie zbrojeń profili i kalendarza (dni robocze / weekendy)
- zapis dziennych terminów zakończenia produkcji (snapshot JSON)
- generowanie raportu zapotrzebowania SAP (kolejność wg Hydry)
- eksport raportu do DOCX (Word)

## Wymagania
- Python 3.10+
- pandas
- customtkinter
- python-docx
- openpyxl
- dostęp do bazy danych (ODBC) – opcjonalnie

## Uruchomienie
python app.py
