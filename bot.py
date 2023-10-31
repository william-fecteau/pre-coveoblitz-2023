from prediction import compute_predicted_collisions
from game_message import *
from actions import *
from custom_message import *

from selection import select_target
from tracking import get_pending_collisions


class Bot:
    def __init__(self):
        self.new_pending_collisions: list[PredictedCollision] = []
        self.last_shot: PredictedCollision | None = None

        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage) -> list[LookAtAction | RotateAction | ShootAction]:
        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []

        # Tracking rockets to get pending collisions
        self.new_pending_collisions, child_collisions = get_pending_collisions(
            self.last_shot, self.new_pending_collisions, game_message)
        self.last_shot = None

        # Predicting all possible collisions
        predicted_collisions: list[PredictedCollision] = compute_predicted_collisions(self.new_pending_collisions,
                                                                                      game_message)

        # Add child collisions to predicted collisions
        predicted_collisions.extend(child_collisions)

        # Choosing the best possible collision
        selected_collision: PredictedCollision = select_target(
            predicted_collisions, game_message)

        if selected_collision is None:
            return []  # TODO: Maybe fallback to something?

        self.last_shot = selected_collision
        return [
            LookAtAction(selected_collision.collision_position),
            ShootAction()
        ]
