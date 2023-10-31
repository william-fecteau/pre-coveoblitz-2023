
import copy
from math import sqrt
from custom_message import *
from prediction import *


def get_pending_collisions(last_shot: PredictedCollision | None, pending_collisions: list[PredictedCollision], game_message: GameMessage) -> list[PredictedCollision]:
    if last_shot is not None and len(game_message.rockets) > 0:
        last_shot.rocket = game_message.rockets[-1]
        pending_collisions.append(last_shot)

    updated_pending_collisions = []
    for collision in pending_collisions:
        if not does_rocket_id_exists(collision.rocket.id, game_message):
            continue

        if not does_meteor_id_exists(collision.meteor.id, game_message):
            continue

        are_colliding, collision_time = will_collide(
            collision.rocket, collision.meteor)
        if not are_colliding:
            continue

        updated_collision = copy.deepcopy(collision)
        updated_collision.collision_time = collision_time
        # TODO: Should we also update collision_position?
        updated_pending_collisions.append(updated_collision)

    return updated_pending_collisions


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
    return meteor_id in [meteor.id for meteor in game_message.meteors]


def does_rocket_id_exists(rocket_id: int, game_message: GameMessage) -> bool:
    return rocket_id in [rocket.id for rocket in game_message.rockets]
