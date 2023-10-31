
import copy
from math import cos, sin, sqrt

import numpy as np
from numpy import radians
from custom_message import *
from prediction import *


def get_pending_collisions(last_shot: PredictedCollision | None, pending_collisions: list[PredictedCollision], game_message: GameMessage) -> list[PredictedCollision]:
    if last_shot is not None and len(game_message.rockets) > 0:
        last_shot.rocket = game_message.rockets[-1]
        pending_collisions.append(last_shot)

    updated_pending_collisions = []
    all_child_collisions = []
    for collision in pending_collisions:
        if not does_rocket_id_exists(collision.rocket.id, game_message):
            continue

        if not does_meteor_id_exists(collision.meteor.id, game_message):
            continue

        if collision.meteor.id == -1:
            # TODO: Try to find the child meteor or else we won't be able to calculate child_collisions for it
            continue

        are_colliding, collision_time = will_collide(
            collision.rocket, collision.meteor)
        if not are_colliding:
            continue

        if collision.meteor.meteorType != MeteorType.Small:
            child_collisions = get_child_collisions(
                collision.meteor, collision.collision_position, collision_time, game_message)
            all_child_collisions.extend(child_collisions)

        updated_collision = copy.deepcopy(collision)
        updated_collision.collision_time = collision_time
        # TODO: Should we also update collision_position?
        updated_pending_collisions.append(updated_collision)

    return updated_pending_collisions, all_child_collisions


def get_child_collisions(parent_meteor: Meteor, parent_collision_position: Vector, parent_collision_time: float, game_message: GameMessage) -> list[PredictedCollision]:
    child_collisions: list[PredictedCollision] = []

    for child in game_message.constants.meteorInfos[parent_meteor.meteorType].explodesInto:
        launch_time = game_message.tick

        meteor_size: float = game_message.constants.meteorInfos[child.meteorType].size
        child_meteor: Meteor = Meteor(
            id=-1, meteorType=child.meteorType, position=Vector(0, 0), velocity=Vector(0, 0), size=meteor_size)
        split_angle: float = radians(child.approximateAngle)
        parent_speed: float = np.linalg.norm(
            [parent_meteor.velocity.x, parent_meteor.velocity.y])
        speed_ratio: float = game_message.constants.meteorInfos[
            child.meteorType].approximateSpeed / parent_speed
        child_meteor.velocity = Vector(
            x=speed_ratio * (cos(split_angle)*parent_meteor.velocity.x -
                             sin(split_angle)*parent_meteor.velocity.y),
            y=speed_ratio * (sin(split_angle)*parent_meteor.velocity.x +
                             cos(split_angle)*parent_meteor.velocity.y)
        )

        child_meteor.position = get_collision_position(parent_collision_position, child_meteor.velocity, game_message.cannon.position,
                                                       game_message.constants.rockets.speed, parent_collision_time, launch_time)

        if child_meteor.position is not None and uncertainty_check(child_meteor, parent_collision_position, game_message):
            collision_position = child_meteor.position
            collision_time = estimate_collision_time(
                child_meteor.position, launch_time, game_message)

            child_meteor.position = parent_collision_position

            predicted_collision = PredictedCollision(launch_time=game_message.tick,
                                                     collision_time=collision_time,
                                                     collision_position=collision_position,
                                                     rocket=None,
                                                     meteor=child_meteor,
                                                     parent_meteor=parent_meteor)
            child_collisions.append(predicted_collision)

    return child_collisions


def will_collide(rocket: Projectile, meteor: Meteor) -> bool:
    # Check if rocket and meteor will collide and when
    r_vel_x, r_vel_y = rocket.velocity.x, rocket.velocity.y
    m_vel_x, m_vel_y = meteor.velocity.x, meteor.velocity.y
    r_pos_x, r_pos_y = rocket.position.x, rocket.position.y
    m_pos_x, m_pos_y = meteor.position.x, meteor.position.y

    mintime = -(r_pos_x*r_vel_x - r_vel_x*m_pos_x - (r_pos_x - m_pos_x)*m_vel_x + r_pos_y*r_vel_y - r_vel_y*m_pos_y - (r_pos_y - m_pos_y)*m_vel_y) / \
        (r_vel_x**2 - 2*r_vel_x*m_vel_x + m_vel_x**2 +
         r_vel_y**2 - 2*r_vel_y*m_vel_y + m_vel_y**2)

    mindist = sqrt((mintime*(r_vel_x - m_vel_x) + r_pos_x - m_pos_x)
                   ** 2 + (mintime*(r_vel_y - m_vel_y) + r_pos_y - m_pos_y)**2)
    will_collide = mindist < meteor.size + rocket.size

    return will_collide, mintime


def does_meteor_id_exists(meteor_id: int, game_message: GameMessage) -> bool:
    if meteor_id == -1:
        return True  # Child meteor, it might not have spawned yet

    return meteor_id in [meteor.id for meteor in game_message.meteors]


def does_rocket_id_exists(rocket_id: int, game_message: GameMessage) -> bool:
    return rocket_id in [rocket.id for rocket in game_message.rockets]


def uncertainty_check(meteor: Meteor, initial_position: Vector, game_message: GameMessage) -> bool:
    large_meteor_uncertainty: float = 0.3
    medium_meteor_uncertainty: float = 0.6
    small_meteor_uncertainty: float = 1.0

    speed_uncertainty = large_meteor_uncertainty if meteor.meteorType == MeteorType.Large \
        else medium_meteor_uncertainty if meteor.meteorType == MeteorType.Medium \
        else small_meteor_uncertainty
    distance_to_travel = distance_between_vectors(
        meteor.position, initial_position)
    position_uncertainty = distance_to_travel * speed_uncertainty

    rocket_vector = [meteor.position.x - game_message.cannon.position.x,
                     meteor.position.y - game_message.cannon.position.y]
    rocket_vector /= np.linalg.norm(rocket_vector)
    meteor_vector = [meteor.velocity.x, meteor.velocity.y]
    meteor_vector /= np.linalg.norm(meteor_vector)

    uncertainty = (1 - abs(np.dot(rocket_vector, meteor_vector))
                   ) * position_uncertainty

    return uncertainty < meteor.size + game_message.constants.rockets.size
