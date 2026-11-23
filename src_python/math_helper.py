# src_python/math_helper.py

class MathHelper:
    """Математический модуль расчета координат (экономит токены ИИ)"""

    @staticmethod
    def get_centered_rect(width: float, length: float) -> tuple:
        """Координаты прямоугольника с центром в (0, 0)"""
        half_w = width / 2.0
        half_l = length / 2.0
        return (-half_w, -half_l, half_w, half_l)

    @staticmethod
    def get_corner_holes(width: float, length: float, offset: float) -> list:
        """Координаты центров 4 отверстий по углам (отступ по ГОСТ от края до центра)"""
        x = (width / 2.0) - offset
        y = (length / 2.0) - offset
        return [(-x, -y), (-x, y), (x, y), (x, -y)]