
from custom_message import *
from game_message import *
from utils import distance_between_vectors


def compute_predicted_collisions(pending_collisions: list[PredictedCollision], game_message: GameMessage) -> list[PredictedCollision]:
    p_rocket: Vector = game_message.cannon.position
    v_rocket: float = game_message.constants.rockets.speed

    predicted_collisions: list[PredictedCollision] = []

    for meteor in game_message.meteors:
        if meteor.id in [collision.meteor.id for collision in pending_collisions]:
            continue

        collision_point = get_collision_position(
            meteor.position, meteor.velocity, p_rocket, v_rocket)

        if collision_point is not None:
            launch_time = game_message.tick
            collision_time = estimate_collision_time(
                collision_point, launch_time, game_message)

            predicted_collision = PredictedCollision(launch_time=game_message.tick,
                                                     collision_time=collision_time,
                                                     collision_position=collision_point,
                                                     rocket=None,
                                                     meteor=meteor,
                                                     parent_meteor=None)

            predicted_collisions.append(predicted_collision)

    return predicted_collisions


def get_collision_position(p0_meteor: Vector, v_meteor: Vector, p0_rocket: Vector, v_rocket: float,
                           t0_meteor: float = 0.0, t0_rocket: float = 0.0) -> [Vector | None]:
    rocket_lead: float = t0_meteor - t0_rocket
    if rocket_lead < 0:
        return None

    delta_t: float = 0.0
    rate: float = 0.02
    error: float = 1000.0
    iteration: int = 0
    while abs(error) > 0.1 and iteration < 100:
        position = Vector(x=p0_meteor.x + delta_t *
                          v_meteor.x, y=p0_meteor.y + delta_t * v_meteor.y)
        rocket_travel_distance = (rocket_lead + delta_t) * v_rocket
        cannon_target_distance = distance_between_vectors(position, p0_rocket)
        error = cannon_target_distance - rocket_travel_distance
        delta_t += rate * error
        iteration += 1

    if iteration == 100:
        return None
    else:
        return position


def estimate_collision_time(collision_point: Vector, launch_time: float, game_message: GameMessage) -> float:
    p_rocket: Vector = game_message.cannon.position
    v_rocket: float = game_message.constants.rockets.speed

    return launch_time + distance_between_vectors(p_rocket, collision_point) / v_rocket
