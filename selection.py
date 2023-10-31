from game_message import *
from custom_message import *


def select_target(predicted_collisions: list[PredictedCollision], game_message: GameMessage) -> PredictedCollision | None:
    game_bounds = [
        game_message.cannon.position.x+10,
        game_message.constants.world.width,
        0,
        game_message.constants.world.height
    ]

    # Removing out of bounds collisions
    in_bounds_collisions: list[PredictedCollision] = [
        collision for collision in predicted_collisions if is_inside_bounds(collision.collision_position, game_bounds)]

    small_collisions: list[PredictedCollision] = [
        collision for collision in in_bounds_collisions if collision.meteor.meteorType == MeteorType.Small]
    medium_collisions: list[PredictedCollision] = [
        collision for collision in in_bounds_collisions if collision.meteor.meteorType == MeteorType.Medium]
    large_collisions: list[PredictedCollision] = [
        collision for collision in in_bounds_collisions if collision.meteor.meteorType == MeteorType.Large]

    candidate_collisions = small_collisions if small_collisions else medium_collisions if medium_collisions else large_collisions

    sorted_collisions = sorted(candidate_collisions,
                               key=lambda collision: (get_x_distance_from_cannon(collision.collision_position, game_message),
                                                      get_y_distance_from_screen_center(collision.collision_position, game_message)))

    return sorted_collisions[0] if sorted_collisions else None


def get_x_distance_from_cannon(position: Vector, game_message: GameMessage) -> float:
    return abs(position.x - game_message.cannon.position.x)


def get_y_distance_from_screen_center(position: Vector, game_message: GameMessage) -> float:
    return abs(position.y - game_message.constants.world.height/2.0)


def is_inside_bounds(position: Vector, bounds: list[int]) -> bool:
    return (bounds[0] < position.x < bounds[1] and
            bounds[2] < position.y < bounds[3])
