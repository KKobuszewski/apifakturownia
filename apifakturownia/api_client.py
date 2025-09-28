import os
import requests
from datetime import date
from typing import List, Literal, Optional, Any, Dict, Type, Union
from pydantic import BaseModel, Field, conlist, ValidationError as PydanticValidationError

from apifakturownia.models import *
from apifakturownia.errors import *

class InvoicesEndpoint:
    """Zarządca endpointu /invoices, implementujący logikę CRUD+."""

    def __init__(self, client: 'FakturowniaApiClient'):
        self.client = client
        self.endpoint_base = '/invoices.json'

    def create_invoice(self, invoice_data: InvoiceDTO) -> InvoiceDTO:
        """Dodaje nową fakturę (POST /invoices.json).[3]"""
        payload = {'invoice': invoice_data.model_dump(by_alias=True, exclude_none=True)}
        response_data = self.client._make_request('POST', self.endpoint_base, json_data=payload)
        return InvoiceDTO.model_validate(response_data)

    def get_invoice(self, invoice_id: int) -> InvoiceDTO:
        """Pobiera pojedynczą fakturę po ID (GET /invoices/{id}.json).[3]"""
        endpoint = f'/invoices/{invoice_id}.json'
        response_data = self.client._make_request('GET', endpoint)
        # Odpowiedź API Fakturownia często zwraca obiekt bezpośrednio, bez opakowania 'invoice'
        return InvoiceDTO.model_validate(response_data)

    def list_invoices(self, period: str = 'this_month', date_from: Optional[date] = None, date_to: Optional[date] = None,
                      page: int = 1, per_page: int = 100, include_positions: bool = False, **kwargs) -> List:
        """Pobiera listę faktur z filtrowaniem i paginacją (GET /invoices.json).[2, 3]"""
        params = {
            'period': period,
            'page': page,
            'per_page': min(per_page, 100) # Ograniczenie do max 100 [2]
        }
        if date_from:
            params['date_from'] = date_from.isoformat()
        if date_to:
            params['date_to'] = date_to.isoformat()
        if include_positions:
             params['include_positions'] = 'true'

        params.update(kwargs) # Dodatkowe parametry jak 'kind', 'number'

        response_data = self.client._make_request('GET', self.endpoint_base, params=params)

        # API zwraca listę słowników, które musimy zwalidować jako DTO
        return

    def update_invoice(self, invoice_id: int, update_data: Union]) -> InvoiceDTO:
        """Aktualizuje istniejącą fakturę (PUT /invoices/{id}.json).[2]"""
        endpoint = f'/invoices/{invoice_id}.json'

        if isinstance(update_data, InvoiceDTO):
            payload = {'invoice': update_data.model_dump(by_alias=True, exclude_none=True)}
        else:
            # W przypadku, gdy użytkownik przekazuje surowy słownik do aktualizacji (częściowa aktualizacja)
            payload = {'invoice': update_data}

        response_data = self.client._make_request('PUT', endpoint, json_data=payload)
        return InvoiceDTO.model_validate(response_data)

    def delete_invoice_permanently(self, invoice_id: int) -> bool:
        """Trwale usuwa fakturę (DELETE /invoices/{id}.json).[2]"""
        endpoint = f'/invoices/{invoice_id}.json'
        self.client._make_request('DELETE', endpoint)
        return True # Brak ciała, sukces jeśli status 200/204

    def void_invoice(self, invoice_id: int, reason: Optional[str] = None) -> bool:
        """Anuluje fakturę zmieniając jej status (POST /invoices/{id}/change_status.json).[2, 5]"""
        endpoint = f'/invoices/{invoice_id}/change_status.json'
        params = {'status': VOID_STATUS}
        if reason:
            # Chociaż API wymaga podania powodu w GUI [6], API może akceptować go w body lub jako parametr.
            # Domyślnie używamy tylko statusu, gdyż tak sugeruje przykład curl.[2]
            pass

        # Metoda POST używa tokena w query string dla tego endpointu zmiany statusu.
        self.client._make_request('POST', endpoint, params=params)
        return True

class FakturowniaApiClient:
    """Główna klasa klienta Fakturownia API, zarządzająca autoryzacją i komunikacją."""

    def __init__(self, domain: str, api_token: str, request_timeout: int = 10):
        self.base_url = f"https://{domain}.fakturownia.pl"
        self.api_token = api_token
        self.timeout = request_timeout
        self.session = requests.Session()
        self.invoices = InvoicesEndpoint(self)

        # Ustawienie nagłówków JSON dla wszystkich zapytań
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

    def _make_request(self, method: str, endpoint: str,
                      request_params: Optional[Any] = None,
                      json_data: Optional[Any] = None) -> Any:

        full_url = self.base_url + endpoint
        request_params = request_params.copy() if request_params else {}
        request_json = json_data.copy() if json_data else {}

        # Dynamiczne wstrzykiwanie tokena autoryzacyjnego:
        # 1. Metody zapisu (POST, PUT) - token w ciele JSON [1]
        if method in:
            # Token musi być w głównym obiekcie JSON
            if request_json is None:
                request_json = {}
            request_json['api_token'] = self.api_token

        # 2. Metody odczytu/usuwania (GET, DELETE) - token w query string [2, 3]
        elif method in:
            request_params['api_token'] = self.api_token

        try:
            response = self.session.request(
                method,
                full_url,
                params=request_params,
                json=request_json,
                timeout=self.timeout
            )

        except requests.exceptions.RequestException as e:
            # Obsługa ogólnych błędów sieciowych lub timeoutów
            raise FakturowniaAPIException(f"Błąd sieciowy podczas komunikacji z API: {e}")

        # Weryfikacja statusu HTTP
        if 200 <= response.status_code < 300:
            if response.status_code == 204 or not response.content: # DELETE często zwraca 204 No Content
                return None
            try:
                return response.json()
            except requests.JSONDecodeError:
                raise FakturowniaAPIException("Nie udało się zdekodować odpowiedzi JSON.")

        # Mapowanie błędów na niestandardowe wyjątki
        error_details = response.json() if response.content else None
        error_message = f"Błąd API Fakturownia (HTTP {response.status_code}): {response.text}"

        if response.status_code == 400:
            raise ValidationError(error_message, response.status_code, error_details)
        elif response.status_code == 401 or response.status_code == 403:
            raise AuthenticationError(error_message, response.status_code, error_details)
        elif response.status_code == 404:
            raise ResourceNotFoundError(error_message, response.status_code, error_details)
        elif 500 <= response.status_code < 600:
            raise ServerError(error_message, response.status_code, error_details)
        else:
            raise FakturowniaAPIException(error_message, response.status_code, error_details)
