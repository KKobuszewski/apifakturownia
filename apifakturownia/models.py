from datetime import date
from typing import List, Literal, Optional, Any, Dict, Type, Union
from pydantic import BaseModel, Field, conlist, ValidationError as PydanticValidationError


# --- definitions of constants and literals  ---

# Dopuszczalne rodzaje dokumentów (kind) [1, 2]
DocumentKind = Literal['vat', 'proforma', 'correction', 'advance', 'final', 'cost', 'accounting_note']

# Dopuszczalne stawki VAT (tax) - numeryczne lub specjalne ciągi [2]
VatRateLiteral = Literal['np', 'zw', 'disabled']
VatRate = Union[int, float, str]

# Status anulowania dla endpointu change_status [2, 5]
VOID_STATUS = 'anulowana'



# --- data models (DTO) in Pydantic ---

class CorrectionAttributesDTO(BaseModel):
    """Model dla pól 'before' i 'after' w pozycjach korygujących.[1]"""
    name: Optional[str] = None
    quantity: Optional[Union[int, float]] = None
    total_price_gross: Optional[Union[str, float]] = None
    tax: Optional[float] = 23.0
    kind: Optional[str] = Field('correction_before', exclude=True) # Wymagane przez API, ale domyślne dla kontekstu


class InvoicePositionDTO(BaseModel):
    """Model dla pojedynczej pozycji na fakturze.[4]"""
    id: Optional[int] = None
    name: str
    quantity: Union[int, float] = Field(..., gt=0, description="Ilość musi być dodatnia, chyba że jest to korekta.")
    total_price_gross: Union[str, float]
    tax: VatRate

    # Pola specyficzne dla faktur korygujących [1]
    kind: Optional[str] = None # Używane np. "correction" dla pozycji korygującej
    correction_before_attributes: Optional = None
    correction_after_attributes: Optional = None

    # Konfiguracja Pydantic
    class Config:
        populate_by_name = True


class InvoiceDTO(BaseModel):
    """Główny model danych dla faktury.[1, 4]"""
    # Pola obowiązkowe
    kind: DocumentKind
    sell_date: date
    issue_date: date

    # Dane sprzedawcy
    seller_name: Optional[str] = None
    seller_tax_no: Optional[str] = None

    # Dane nabywcy
    buyer_name: Optional[str] = None
    buyer_tax_no: Optional[str] = None
    buyer_email: Optional[str] = None

    # Termin płatności i metoda
    payment_to: Optional[date] = None
    payment_method: Optional[str] = Field('Przelew', description="Brak listy enumów, używamy stringa [2]")

    # Zagnieżdżone pozycje
    positions: conlist(InvoicePositionDTO, min_length=1)

    # Pola dla faktur korygujących
    correction_reason: Optional[str] = None # Wymagane dla kind='correction' [1]
    invoice_id: Optional[int] = None # ID faktury korygowanej [1]
    from_invoice_id: Optional[int] = None # Alias dla invoice_id [1]

    # Pola tylko do odczytu (parsujemy w odpowiedzi GET, ignorujemy w POST/PUT)
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    invoice_url: Optional[str] = None # Link do podglądu PDF [2]

    # Konfiguracja Pydantic dla serializacji
    class Config:
        populate_by_name = True
        # Konfiguracja, aby umożliwić parsowanie pól tylko do odczytu z odpowiedzi API
        extra = 'ignore'
