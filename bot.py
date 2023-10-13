from game_message import *
from actions import *
from math import atan, sqrt, cos
import copy

class Bot:
    def __init__(self):
        self.targetted_meteor_ids: list[int] = []
        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage) -> list[LookAtAction | RotateAction | ShootAction]:
        print(f"Score: {game_message.score}")

        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []
        
        # Computing the collision position of each meteor
        meteors_collisions: list[Meteor] = self.compute_meteors_collisions(game_message)

        # Targetting a meteor
        target_meteor: Meteor = self.select_target_meteor(meteors_collisions, game_message)
        if target_meteor is None:
            return []
        
        # Updating the targeted ids
        self.update_targeted_ids(target_meteor.id, game_message.meteors)

        # Moving the cannon to hit the targetted meteor      
        return [
            LookAtAction(target_meteor.position),
            ShootAction()
        ]
    

    def compute_meteors_collisions(self, game_message: GameMessage) -> list[Meteor]:
        p_rocket: Vector = game_message.cannon.position
        v_rocket: float = game_message.constants.rockets.speed
        meteors_collisions: list[Meteor] = []
        for meteor in game_message.meteors:
            collision_point: Vector = self.get_collision_position(meteor.position, meteor.velocity, p_rocket, v_rocket)
            if collision_point is not None:
                meteor_copy: Meteor = copy.deepcopy(meteor)
                meteor_copy.position = collision_point
                meteors_collisions.append(meteor_copy)
        return meteors_collisions
    

    def select_target_meteor(self, meteors: list[Meteor], game_message: GameMessage) -> Meteor:
        bounds: list[int] = [game_message.cannon.position.x, game_message.constants.world.width, 0, game_message.constants.world.height]
        reachable_meteors: list[Meteor] = [meteor for meteor in meteors if self.is_inside_bounds(meteor.position, bounds)]
        candidate_meteors: list[Meteor] = [meteor for meteor in reachable_meteors if meteor.id not in self.targetted_meteor_ids]
        sorted_candidates: list[Meteor] = sorted(sorted(candidate_meteors, key=lambda meteor: meteor.position.x), key=lambda meteor: meteor.meteorType, reverse=True)
        return sorted_candidates[0] if sorted_candidates else None


    def get_collision_position(self, p_meteor: Vector, v_meteor: Vector, p_rocket: Vector, v_rocket: float) -> Vector:
        # a,b,c are bad names but used to simplify the equations
        a: float = (p_rocket.y - p_meteor.y) / (p_rocket.x - p_meteor.x)
        b: float = (a * v_meteor.x - v_meteor.y) / v_rocket
        c: float = a**2 - b**2 + 1
        if c < 0:
            return None
        theta: float = 2*atan((sqrt(c) - 1)/(a + b)) 
        t: float = (p_rocket.x - p_meteor.x) / (v_meteor.x - v_rocket * cos(theta))
        collision_point: Vector = Vector(x=p_meteor.x + t * v_meteor.x, y=p_meteor.y + t * v_meteor.y)
        return collision_point
    

    def is_inside_bounds(self, position, bounds) -> bool:
        return (bounds[0] <= position.x <= bounds[1] and \
                bounds[2] <= position.y <= bounds[3])
    

    def update_targeted_ids(self, target_id, meteors: list[Meteor]) -> None:
        for id in self.targetted_meteor_ids:
            if id not in [meteor.id for meteor in meteors]:
                self.targetted_meteor_ids.remove(id)
        if target_id not in self.targetted_meteor_ids:
            self.targetted_meteor_ids.append(target_id)


    def distance(self, p1, p2) -> float:
        return sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)