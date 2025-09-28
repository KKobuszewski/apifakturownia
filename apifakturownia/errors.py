

class FakturowniaAPIException(Exception):
    """Bazowa klasa dla wyjątków API Fakturownia."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

class AuthenticationError(FakturowniaAPIException):
    """Błąd 401/403: Niepoprawny token API lub brak dostępu."""
    pass

class ValidationError(FakturowniaAPIException):
    """Błąd 400: Niepoprawne dane przesłane w zapytaniu."""
    pass

class ResourceNotFoundError(FakturowniaAPIException):
    """Błąd 404: Zasób nie został znaleziony."""
    pass

class ServerError(FakturowniaAPIException):
    """Błąd 5xx: Błąd po stronie serwera Fakturownia."""
    pass
