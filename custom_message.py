from dataclasses import dataclass
from game_message import *


@dataclass
class PredictedCollision:
    collision_time: float
    launch_time: int
    collision_position: Vector
    # None means the rocket was not launched yet
    rocket: Projectile | None
    meteor: Meteor
    # None means the meteor is not a child position prediction
    parent_meteor: Meteor | None
