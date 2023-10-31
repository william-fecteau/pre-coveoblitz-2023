from dataclasses import dataclass
from typing import List

import numpy as np
from numpy import cos, sin

from game_message import MeteorType, Vector, Meteor, ExplosionInfos, GameMessage



@dataclass
class LifetimeEvaluation:
    meteor: Meteor
    time_to_exit: float
    children: List[LifetimeEvaluation] = None


class LifetimeEstimator:
    def __init__(self, game_bounds: Vector):
        self.game_bounds = game_bounds

    def time_to_exit_field(self, position: Vector, velocity: Vector) -> float:
        t_exit_x = (self.game_bounds.x - position.x) / velocity.x if velocity.x != 0 else float('inf')
        t_exit_y = (self.game_bounds.y - position.y) / velocity.y if velocity.y != 0 else float('inf')

        return min(t for t in [t_exit_x, t_exit_y] if t >= 0)

    def evaluate_meteor_lifetime(self, meteor: Meteor, game_message: GameMessage) -> LifetimeEvaluation:
        time_left = self.time_to_exit_field(meteor.position, meteor.velocity)

        # Check if the meteor is in the first half of the game window
        is_in_first_half = meteor.position.x <= self.game_bounds.x / 2

        # Check if the meteor is not in the last quarter of the game window
        is_not_in_last_quarter = meteor.position.x < 3 * (self.game_bounds.x / 4)

        if meteor.meteorType == MeteorType.Large and is_in_first_half:
            medium_meteors = self.spawn_children_from_parent(meteor, game_message)
            children_evaluations = [self.evaluate_meteor_lifetime(child) for child in medium_meteors]
            return LifetimeEvaluation(meteor, time_left, children_evaluations)

        elif meteor.meteorType == MeteorType.Medium and is_not_in_last_quarter:
            small_meteors = self.spawn_children_from_parent(meteor, game_message)
            children_evaluations = [self.evaluate_meteor_lifetime(child) for child in small_meteors]
            return LifetimeEvaluation(meteor, time_left, children_evaluations)

        return LifetimeEvaluation(meteor, time_left)

    def spawn_children_from_parent(self, parent_meteor: Meteor, game_message: GameMessage) -> List[Meteor]:
        children_meteors = []

        for child_info in game_message.constants.meteorInfos[parent_meteor.meteorType].explodesInto:
            meteor_size: float = game_message.constants.meteorInfos[child_info.meteorType].size
            child_meteor: Meteor = Meteor(id=-1, meteorType=child_info.meteorType, position=parent_meteor.position,
                                          velocity=Vector(0, 0), size=meteor_size)
            split_angle: float = np.radians(child_info.approximateAngle)
            parent_speed: float = np.linalg.norm([parent_meteor.velocity.x, parent_meteor.velocity.y])
            speed_ratio: float = game_message.constants.meteorInfos[
                                     child_info.meteorType].approximateSpeed / parent_speed
            child_meteor.velocity = Vector(
                x=speed_ratio * (
                        cos(split_angle) * parent_meteor.velocity.x - sin(split_angle) * parent_meteor.velocity.y),
                y=speed_ratio * (
                        sin(split_angle) * parent_meteor.velocity.x + cos(split_angle) * parent_meteor.velocity.y)
            )
            children_meteors.append(child_meteor)

        return children_meteors
