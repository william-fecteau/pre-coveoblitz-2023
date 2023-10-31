from math import sqrt
from game_message import Vector


def distance_between_vectors(v1: Vector, v2: Vector) -> float:
    return sqrt((v1.x - v2.x)**2 + (v1.y - v2.y)**2)
