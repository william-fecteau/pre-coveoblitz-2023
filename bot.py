from prediction import compute_predicted_collisions
from game_message import *
from actions import *
from custom_message import *
from math import sqrt, cos, sin, radians
import copy
import numpy as np

from selection import select_target
from tracking import get_pending_collisions


class Collision:
    def __init__(self, rocket: Projectile, meteor: Meteor, time: float):
        self.rocket: Projectile = rocket
        self.meteor: Meteor = meteor
        self.time: float = time


class Shot:
    def __init__(self, id: Projectile, target: Meteor, time: float, reason: str):
        self.rocket_id: int = id
        self.target: Meteor = target
        self.time: float = time
        self.reason: str = reason


class Bot:
    def __init__(self):
        self.game_bounds: list[int] = []
        self.target_queue: list[Meteor] = []
        self.large_meteor_uncertainty: float = 0.3
        self.medium_meteor_uncertainty: float = 0.6
        self.small_meteor_uncertainty: float = 1.0

        self.new_pending_collisions: list[PredictedCollision] = []
        self.last_shot: PredictedCollision | None = None

        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage) -> list[LookAtAction | RotateAction | ShootAction]:
        # print(f"Score: {game_message.score}")

        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []

        # Tracking rockets to get pending collisions
        self.new_pending_collisions = get_pending_collisions(
            self.last_shot, self.new_pending_collisions, game_message)
        self.last_shot = None

        # Predicting all possible collisions
        predicted_collisions: list[PredictedCollision] = compute_predicted_collisions(self.new_pending_collisions,
                                                                                      game_message)

        # Choosing the best possible collision
        selected_collision: PredictedCollision = select_target(
            predicted_collisions, game_message)

        if selected_collision is None:
            return []

        # target_meteor: Meteor = self.select_target_meteor(meteors_collisions, game_message)
        # if target_meteor is None:
        #     return []
        # elif target_meteor.meteorType in [MeteorType.Large, MeteorType.Medium] and self.reason == "Score":
        #     collision_time: float = self.estimate_collision_time(target_meteor, game_message.tick, game_message)
        #     self.target_child_meteors(target_meteor, collision_time, game_message)

        self.last_shot = selected_collision
        return [
            LookAtAction(selected_collision.collision_position),
            ShootAction()
        ]

    def compute_meteors_collisions(self, game_message: GameMessage) -> list[Meteor]:
        p_rocket: Vector = game_message.cannon.position
        v_rocket: float = game_message.constants.rockets.speed
        meteors_collisions: list[Meteor] = []
        for meteor in game_message.meteors:
            collision_point = self.get_collision_position(
                meteor.position, meteor.velocity, p_rocket, v_rocket)
            if collision_point is not None:
                meteor_copy: Meteor = copy.deepcopy(meteor)
                meteor_copy.position = collision_point
                meteors_collisions.append(meteor_copy)
            else:
                print(
                    f'Skipping collision computation for {meteor.meteorType} at position ({round(meteor.position.x)},{round(meteor.position.y)})')
        return meteors_collisions

    def estimate_collision_time(self, target_meteor: Meteor, launch_time: float, game_message: GameMessage) -> float:
        p_rocket: Vector = game_message.cannon.position
        v_rocket: float = game_message.constants.rockets.speed
        collision_point: Vector = target_meteor.position
        return launch_time + self.distance(p_rocket, collision_point) / v_rocket

    def target_child_meteors(self, parent_meteor: Meteor, parent_collision_time: float, game_message: GameMessage) -> None:

        for child in game_message.constants.meteorInfos[parent_meteor.meteorType].explodesInto:
            # Next rocket will launch after all queued rockets
            launch_time = game_message.tick + \
                (len(self.target_queue) + 1) * \
                game_message.constants.cannonCooldownTicks

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

            child_meteor.position = self.get_collision_position(parent_meteor.position, child_meteor.velocity, game_message.cannon.position,
                                                                game_message.constants.rockets.speed, parent_collision_time, launch_time)
            if child_meteor.position is not None \
                    and self.is_inside_bounds(child_meteor.position) \
                    and self.uncertainty_check(child_meteor, parent_meteor.position, game_message):
                self.target_queue.append(child_meteor)
                print(
                    f'Added {child_meteor.meteorType} meteor colliding at position ({round(child_meteor.position.x)},{round(child_meteor.position.y)}) to target_queue')
                child_collision_time: float = self.estimate_collision_time(
                    child_meteor, launch_time, game_message)
                self.target_child_meteors(
                    child_meteor, child_collision_time, game_message)

    def get_collision_position(self, p0_meteor: Vector, v_meteor: Vector, p0_rocket: Vector, v_rocket: float,
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
            cannon_target_distance = self.distance(position, p0_rocket)
            error = cannon_target_distance - rocket_travel_distance
            delta_t += rate * error
            iteration += 1

        if iteration == 100:
            return None
        else:
            return position

    def uncertainty_check(self, meteor: Meteor, initial_position: Vector, game_message: GameMessage) -> bool:

        speed_uncertainty = self.large_meteor_uncertainty if meteor.meteorType == MeteorType.Large \
            else self.medium_meteor_uncertainty if meteor.meteorType == MeteorType.Medium \
            else self.small_meteor_uncertainty
        distance_to_travel = self.distance(meteor.position, initial_position)
        position_uncertainty = distance_to_travel * speed_uncertainty

        rocket_vector = [meteor.position.x - game_message.cannon.position.x,
                         meteor.position.y - game_message.cannon.position.y]
        rocket_vector /= np.linalg.norm(rocket_vector)
        meteor_vector = [meteor.velocity.x, meteor.velocity.y]
        meteor_vector /= np.linalg.norm(meteor_vector)

        uncertainty = (1 - abs(np.dot(rocket_vector, meteor_vector))
                       ) * position_uncertainty
        return uncertainty < meteor.size + game_message.constants.rockets.size
