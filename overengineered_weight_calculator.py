import numpy as np
from typing import Tuple, Callable
from functools import lru_cache


class VectorField:
    def __init__(self, cannon_position: Tuple[float, float], edge_point: Tuple[int, int]):
        self.a_x, self.a_y = cannon_position
        self.b_x, self.b_y = map(float, edge_point)
        self.m = (self.a_x + self.b_x) / 2
        self.k = 10 / (self.b_x - self.a_x)

    def _f(self, x):
        """Sigmoid function centered between a and b."""
        return 1 / (1 + np.exp(self.k * (x - self.m)))

    @lru_cache(maxsize=None)
    def compute_field(self, x, y, epsilon=1e-10):
        relative_x = x - self.a_x
        relative_y = y - self.a_y
        magnitude = np.sqrt(relative_x ** 2 + relative_y ** 2 + epsilon)
        fx = self._f(x)
        v_x = -fx * relative_x / magnitude
        v_y = -fx * relative_y / magnitude
        return v_x, v_y


class WeightCalculator:
    def __init__(self, vector_battlefield: VectorField, min_speed=2.3, max_speed=16.0):
        self.vector_field = vector_battlefield
        self.min_speed = min_speed
        self.max_speed = max_speed

    def angle_between_vectors(self, v_x1, v_y1, v_x2, v_y2):
        """Compute the angle (in degrees) between two vectors."""
        dot_product = v_x1 * v_x2 + v_y1 * v_y2
        magnitude1 = np.sqrt(v_x1 ** 2 + v_y1 ** 2)
        magnitude2 = np.sqrt(v_x2 ** 2 + v_y2 ** 2)
        cos_theta = dot_product / (magnitude1 * magnitude2)
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        return np.degrees(np.arccos(cos_theta))

    def compute_alignment_weight(self, x, y, velocity_x, velocity_y):
        field_v_x, field_v_y = self.vector_field.compute_field(x, y)
        theta = self.angle_between_vectors(velocity_x, velocity_y, field_v_x, field_v_y)
        theta_mod_180 = abs(theta) % 180
        alignment_weight = 1 - (theta_mod_180 / 90.0)
        return alignment_weight

    def compute_speed_normalization(self, velocity_x, velocity_y):
        velocity_magnitude = np.sqrt(velocity_x ** 2 + velocity_y ** 2)
        normalized_speed = self.min_speed + self.min_speed * (velocity_magnitude / self.max_speed)
        return normalized_speed

    def compute_large_medium_weight(self, x, y, velocity_x, velocity_y):
        alignment_weight = self.compute_alignment_weight(x, y, velocity_x, velocity_y)
        normalized_speed = self.compute_speed_normalization(velocity_x, velocity_y)
        large_medium_weight = alignment_weight * normalized_speed
        return large_medium_weight

    def compute_small_weight(self, x, y, velocity_x, velocity_y):
        _, field_v_y = self.vector_field.compute_field(x, y)

        # Divergence en y seulement
        y_divergence = np.abs(velocity_y - field_v_y)

        # Distance du cannon
        distance_from_a = np.sqrt((x - self.vector_field.a_x) ** 2 + (y - self.vector_field.a_y) ** 2)

        base_weight = 2.0 # to tune
        distance_factor = 0.5 + 0.5 * (
                    distance_from_a / np.sqrt(self.vector_field.a_x ** 2 + self.vector_field.a_y ** 2))
        small_weight = base_weight + y_divergence * distance_factor

        return small_weight

    def compute_weight(self, type_meteor: str, x, y, velocity_x, velocity_y):
        if type_meteor in ['Large', 'Medium']:
            return self.compute_large_medium_weight(x, y, velocity_x, velocity_y)
        elif type_meteor == 'Small':
            return self.compute_small_weight(x, y, velocity_x, velocity_y)


# cas d'utilisation
vector_field = VectorField(cannon_position=(0, 0), edge_point=(10, 10))
weight_calculator = WeightCalculator(vector_field)
weight = weight_calculator.compute_weight('Large', 5, 5, 1, 1)
print(weight)
