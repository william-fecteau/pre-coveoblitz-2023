from dataclasses import dataclass
from typing import List

import numpy as np

from game_message import Meteor, Vector, MeteorType, GameMessage


@dataclass
class LifetimeScore:
    meteor: Meteor
    score: float


class LifetimeScorer:
    def __init__(self, game_bounds: Vector):
        self.game_bounds = game_bounds

    def edge_penalty(self, position: Vector) -> float:
        """Calculate a penalty based on how close the meteor is to the edge using a sigmoid function."""
        distance_to_edge = min(position.y, self.game_bounds.y - position.y)

        t_0 = self.game_bounds.y / 6
        k = 10
        exponent = -k * (distance_to_edge - t_0)

        # Handle very large and very small exponents to avoid overflow
        thresh = 10  # you can adjust this threshold as needed
        if exponent > thresh:
            penalty = 0
        elif exponent < -thresh:
            penalty = 1
        else:
            penalty = 1 / (1 + np.exp(exponent))

        penalty = 0.5 + 0.5 * penalty
        return penalty

    def calculate_score(self, meteor: Meteor) -> float:
        base_score = {
            MeteorType.Large: 3,
            MeteorType.Medium: 2,
            MeteorType.Small: 1,
        }[meteor.meteorType]

        # Apply proximity penalty based on x-axis
        proximity_penalty = (self.game_bounds.x - meteor.position.x) / self.game_bounds.x
        score_x_penalty = base_score / (1 + proximity_penalty)

        # Apply edge penalty based on y-axis using the sigmoid function
        edge_penalty_multiplier = self.edge_penalty(meteor.position)
        final_score = score_x_penalty * edge_penalty_multiplier

        return final_score

    def evaluate_meteor_score(self, meteor: Meteor, game_message: GameMessage) -> LifetimeScore:
        score = self.calculate_score(meteor)

        # Check if the meteor is in the first half of the game window
        is_in_first_half = meteor.position.x <= self.game_bounds.x / 2
        # Check if the meteor is not in the last quarter of the game window
        is_not_in_last_quarter = meteor.position.x < 3 * (self.game_bounds.x / 4)

        if meteor.meteorType == MeteorType.Large and is_in_first_half:
            children = self.spawn_children_from_parent(meteor, game_message)
            for child in children:
                score += 0.5 * self.calculate_score(child)

        elif meteor.meteorType == MeteorType.Medium and is_not_in_last_quarter:
            children = self.spawn_children_from_parent(meteor, game_message)
            for child in children:
                score += 0.3 * self.calculate_score(child)

        elif meteor.meteorType == MeteorType.Medium and not is_not_in_last_quarter:
            score += self.calculate_score(meteor)
            children = self.spawn_children_from_parent(meteor, game_message)
            for child in children:
                self.evaluate_meteor_score(child, game_message)

        elif meteor.meteorType == MeteorType.Large and not is_in_first_half:
            score += self.calculate_score(meteor)
            children = self.spawn_children_from_parent(meteor, game_message)
            for child in children:
                self.evaluate_meteor_score(child, game_message)

        elif meteor.meteorType == MeteorType.Small:
            score += self.calculate_score(meteor)

        return LifetimeScore(meteor, score)

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
                        np.cos(split_angle) * parent_meteor.velocity.x - np.sin(
                    split_angle) * parent_meteor.velocity.y),
                y=speed_ratio * (
                        np.sin(split_angle) * parent_meteor.velocity.x + np.cos(split_angle) * parent_meteor.velocity.y)
            )
            children_meteors.append(child_meteor)
