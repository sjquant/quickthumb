class CanvasValidationError(ValueError):
    pass


class Canvas:
    def __init__(self, width: int, height: int):
        if width <= 0:
            raise CanvasValidationError("width must be > 0")
        if height <= 0:
            raise CanvasValidationError("height must be > 0")

        self.width = width
        self.height = height

    @classmethod
    def from_aspect_ratio(cls, ratio: str, base_width: int):
        width_ratio, height_ratio = ratio.split(":")
        calculated_height = int(base_width * int(height_ratio) / int(width_ratio))
        return cls(base_width, calculated_height)


__all__ = ["Canvas", "CanvasValidationError"]
