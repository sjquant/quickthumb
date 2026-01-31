from pydantic import ValidationError as PydanticValidationError


class QuickthumbError(Exception):
    pass


class ValidationError(QuickthumbError):
    def __init__(self, message: str, original_error: PydanticValidationError | None = None):
        super().__init__(message)
        self._original_error = original_error

    @property
    def original_error(self) -> PydanticValidationError | None:
        return self._original_error


class RenderingError(QuickthumbError):
    pass
