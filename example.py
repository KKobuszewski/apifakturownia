import os
from apifakturownia.errors import (
    ValidationError,
    AuthenticationError
)
from apifakturownia.models import (
    FakturowniaApiClient,
    InvoiceDTO,
    InvoicePositionDTO,
)
from apifakturownia.api_client import FakturowniaApiClient

from datetime import date

# 1. Pobieranie danych autoryzacyjnych ze środowiska
DOMAIN = os.environ.get("FAKTUROWNIA_DOMAIN")
TOKEN = os.environ.get("FAKTUROWNIA_TOKEN")

if not DOMAIN or not TOKEN:
    raise EnvironmentError("Brak zmiennych FAKTUROWNIA_DOMAIN lub FAKTUROWNIA_TOKEN.")

# 2. Inicjalizacja klienta
try:
    api = FakturowniaApiClient(domain=DOMAIN, api_token=TOKEN)

    # 3. Modelowanie danych (z walidacją Pydantic)
    new_position = InvoicePositionDTO(
        name="Usługa programistyczna",
        quantity=1.0,
        total_price_gross=1230.00,
        tax=23.0 # Stawka VAT 23%
    )

    new_invoice = InvoiceDTO(
        kind='vat',
        sell_date=date.today(),
        issue_date=date.today(),
        buyer_name="Nowy Klient",
        buyer_tax_no="1234567890",
        positions=[new_position]
    )

    # 4. Wykonanie operacji (CREATE)
    print("Tworzenie faktury...")
    created_invoice = api.invoices.create_invoice(new_invoice)
    print(f"Faktura utworzona pomyślnie. ID: {created_invoice.id}")

except AuthenticationError:
    print("Błąd autoryzacji: Sprawdź TOKEN lub DOMAIN.")
except ValidationError as e:
    print(f"Błąd walidacji danych przed wysłaniem: {e.details}")
except Exception as e:
    print(f"Nieoczekiwany błąd API: {e}")
