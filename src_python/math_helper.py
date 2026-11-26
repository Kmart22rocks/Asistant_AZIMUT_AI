class MathHelper:
    @staticmethod
    def get_centered_rect(width: float, length: float) -> tuple:
        half_w = width / 2.0
        half_l = length / 2.0
        return (-half_w, -half_l, half_w, half_l)

    @staticmethod
    def get_corner_holes(width: float, length: float, offset: float) -> list:
        x = (width / 2.0) - offset
        y = (length / 2.0) - offset
        return [(-x, -y), (-x, y), (x, y), (x, -y)]