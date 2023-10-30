import numpy as np
from typing import Tuple
from functools import lru_cache


class VectorField:
    """Represents a vector field for the cannon's targeting system."""

    SIGMOID_STEEPNESS = 10.0

    def __init__(self, cannon_position: Tuple[float, float], edge_point: Tuple[int, int]):
        self.a_x, self.a_y = cannon_position
        self.b_x, self.b_y = map(float, edge_point)
        self.mid_point_x = (self.a_x + self.b_x) / 2
        self.sigmoid_scale = self.SIGMOID_STEEPNESS / (self.b_x - self.a_x)

    def _sigmoid(self, x: float) -> float:
        """Sigmoid function centered between a and b."""
        return 1 / (1 + np.exp(self.sigmoid_scale * (x - self.mid_point_x)))

    @lru_cache(maxsize=None)
    def compute_field(self, x: float, y: float, epsilon=1e-10) -> Tuple[float, float]:
        relative_x = x - self.a_x
        relative_y = y - self.a_y
        magnitude = np.sqrt(relative_x ** 2 + relative_y ** 2 + epsilon)
        sigmoid_value = self._sigmoid(x)
        v_x = -sigmoid_value * relative_x / magnitude
        v_y = -sigmoid_value * relative_y / magnitude
        return v_x, v_y


class WeightCalculator:
    """Calculates the weights for targeting based on various factors."""

    def __init__(self, vector_battlefield: VectorField, min_speed=2.3, max_speed=16.0):
        self.vector_field = vector_battlefield
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.absolute_distance = np.sqrt(
            (self.vector_field.a_x - self.vector_field.b_x) ** 2 +
            (self.vector_field.a_y - self.vector_field.b_y) ** 2
        )

    @staticmethod
    def _angle_between_vectors(v_x1, v_y1, v_x2, v_y2) -> float:
        dot_product = v_x1 * v_x2 + v_y1 * v_y2
        magnitude1 = np.sqrt(v_x1 ** 2 + v_y1 ** 2)
        magnitude2 = np.sqrt(v_x2 ** 2 + v_y2 ** 2)
        cos_theta = np.clip(dot_product / (magnitude1 * magnitude2), -1.0, 1.0)
        return np.degrees(np.arccos(cos_theta))

    def _alignment_weight(self, x, y, velocity_x, velocity_y) -> float:
        field_v_x, field_v_y = self.vector_field.compute_field(x, y)
        theta = self._angle_between_vectors(velocity_x, velocity_y, field_v_x, field_v_y)
        theta_mod_180 = abs(theta) % 180
        return max(0, 1 - (theta_mod_180 / 90.0))

    def _divergence_weight(self, x, y, velocity_x, velocity_y) -> float:
        field_v_x, field_v_y = self.vector_field.compute_field(x, y)
        x_divergence = np.abs(velocity_x - field_v_x) / self.max_speed
        y_divergence = np.abs(velocity_y - field_v_y) / self.max_speed
        return np.sqrt(x_divergence ** 2 + y_divergence ** 2)

    def _speed_normalization(self, velocity_x, velocity_y) -> float:
        velocity_magnitude = np.sqrt(velocity_x ** 2 + velocity_y ** 2)
        normalized_speed = self.min_speed + self.min_speed * (velocity_magnitude / self.max_speed)
        return normalized_speed / (2 * self.min_speed)

    def _closest_meteor_weight(self, x, y) -> float:
        distance_from_cannon = np.sqrt((x - self.vector_field.a_x) ** 2 + (y - self.vector_field.a_y) ** 2)
        normalized_distance = distance_from_cannon / (self.absolute_distance / 2)
        SIGMOID_STEEPNESS = -10
        INFLECTION_POINT = 0.5
        return 1 / (1 + np.exp(SIGMOID_STEEPNESS * (normalized_distance - INFLECTION_POINT)))

    def _large_medium_weight(self, x, y, velocity_x, velocity_y) -> float:
        alignment = self._alignment_weight(x, y, velocity_x, velocity_y)
        speed_norm = self._speed_normalization(velocity_x, velocity_y)
        close_weight = self._closest_meteor_weight(x, y)
        return alignment * speed_norm * close_weight * 1.0

    def _small_weight(self, x, y, velocity_x, velocity_y, divergence_weight_factor=1.0, distance_weight_factor=1.0) -> float:
        divergence_weight = self._divergence_weight(x, y, velocity_x, velocity_y)
        closest_weight = self._closest_meteor_weight(x, y)
        combined_value = divergence_weight_factor * divergence_weight + closest_weight * distance_weight_factor
        to_print = 1 / (1 + np.exp(-20.0 * (combined_value - 1.0)))
        print(to_print)
        return to_print

    def compute_weight(self, type_meteor: str, x, y, velocity_x, velocity_y) -> float:
        if type_meteor in ['LARGE', 'MEDIUM']:
            return self._large_medium_weight(x, y, velocity_x, velocity_y)
        elif type_meteor == 'SMALL':
            return self._small_weight(x, y, velocity_x, velocity_y)
        else:
            raise ValueError(f"Invalid meteor type {type_meteor}")
