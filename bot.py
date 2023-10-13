from game_message import *
from actions import *
from math import atan, sqrt, pi, degrees, sin, cos
import numpy as np
import copy

class Bot:
    def __init__(self):
        self.direction = 1
        self.targeted_ids = []
        print("Initializing your super mega duper bot")

    def get_next_move(self, game_message: GameMessage):
        print(f"Score: {game_message.score}")
        if game_message.cannon.cooldown == 0:
            world_width = game_message.constants.world.width
            world_height = game_message.constants.world.height
            cannon_position = game_message.cannon.position
            rocket_speed = game_message.constants.rockets.speed

            meteors_collisions = []
            for meteor in game_message.meteors:
                collision_position = self.compute_collision_position(meteor.position, meteor.velocity, cannon_position, rocket_speed)
                if collision_position is not None:
                    meteor_copy = copy.deepcopy(meteor)
                    meteor_copy.position = collision_position
                    meteors_collisions.append(meteor_copy)

            target_meteor = self.select_target_meteor(meteors_collisions, cannon_position, world_width, world_height)
            if target_meteor is None:
                return []
            
            actions = [
                LookAtAction(target=target_meteor.position),
                ShootAction()
                ]
            
            self.update_targeted_ids(target_meteor.id, game_message.meteors)
            return actions
        else:
            return []
    
    def select_target_meteor(self, meteors, position, world_width, world_height):
        bounds = [position.x, world_width, 0, world_height]
        meteors_in_bounds = [meteor for meteor in meteors if self.is_inside_bounds(meteor.position, bounds)]
        candidate_meteors = [meteor for meteor in meteors_in_bounds if meteor.id not in self.targeted_ids]

        if len(candidate_meteors) == 0:
            return None

        scored_meteors = [(meteor, self.score_meteor(meteor, position)) for meteor in candidate_meteors]
        scored_meteors.sort(key=lambda x: x[1], reverse=True)
        
        return scored_meteors[0][0] if scored_meteors else None
    
    def update_targeted_ids(self, target_id, meteors):
        for id in self.targeted_ids:
            if id not in [meteor.id for meteor in meteors]:
                self.targeted_ids.remove(id)
        if target_id not in self.targeted_ids:
            self.targeted_ids.append(target_id)

    def compute_collision_position(self, p_meteor, v_meteor, p_rocket, v_rocket):
        a = (p_rocket.y - p_meteor.y) / (p_rocket.x - p_meteor.x)
        b = (a * v_meteor.x - v_meteor.y) / v_rocket
        c = a**2 - b**2 + 1
        if c < 0:
            return None
        theta = 2*atan((sqrt(c) - 1)/(a + b))
        t = (p_rocket.x - p_meteor.x) / (v_meteor.x - v_rocket * cos(theta))
        collision_position = Vector(x=p_meteor.x + t * v_meteor.x, y=p_meteor.y + t * v_meteor.y)
        return collision_position

    def is_inside_bounds(self, position, bounds):
        return (bounds[0] <= position.x <= bounds[1] and \
                bounds[2] <= position.y <= bounds[3])
    
    def score_meteor(self, meteor, position):
        distance_score = 1 / self.distance(meteor.position, position)
        size_score = {
            MeteorType.Large: 1,
            MeteorType.Medium: 2,
            MeteorType.Small: 3}[meteor.meteorType]
        
        return distance_score #* size_score
    
    def distance(self, p1, p2):
        return sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)