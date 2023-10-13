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

            # meteors_collisions = copy.deepcopy(game_message.meteors)
            # for meteor in meteors_collisions:
            #     meteor.position = self.compute_collision_position(meteor.position, meteor.velocity, cannon_position, rocket_speed)

            target_meteor = self.select_target_meteor(game_message.meteors, game_message.cannon.position, world_width, world_height)
            if target_meteor is None:
                return []

            # Compute the angle to shoot the meteor
            p_meteor = target_meteor.position
            v_meteor = target_meteor.velocity
            p_rocket = game_message.cannon.position
            v_rocket = game_message.constants.rockets.speed
            target_angle = self.compute_target_angle(p_meteor, v_meteor, p_rocket, v_rocket)
            if target_angle is None:
                print("No solution found")
                return []

            # Find delta between current angle and target angle
            delta_angle = target_angle - game_message.cannon.orientation

            # Shoot the meteor if the cooldown is 0
            actions = [
                RotateAction(angle=delta_angle),
                ShootAction()
                ]
            
            self.update_targeted_ids(target_meteor.id, game_message.meteors)
            return actions
        else:
            return []
    
    def select_target_meteor(self, meteors, position, world_width, world_height):
        candidate_meteors = [meteor for meteor in meteors if meteor.id not in self.targeted_ids
                            and self.is_inside_frame(meteor.position, world_width, world_height, position)]
        if len(candidate_meteors) == 0 and len(meteors) > 0:
            return meteors[np.random.randint(0, len(meteors))]
        elif len(candidate_meteors) == 0:
            return None
        closest_meteor = meteors[0]
        closest_distance = self.distance(closest_meteor.position, position)
        for meteor in candidate_meteors:
            distance = self.distance(meteor.position, position)
            if distance < closest_distance:
                closest_meteor = meteor
                closest_distance = distance

        scored_meteors = [(meteor, self.score_meteor(meteor, position, world_width, world_height)) for meteor in candidate_meteors]
        scored_meteors.sort(key=lambda x: x[1], reverse=True)
        
        return scored_meteors[0][0] if scored_meteors else None
    
    def distance(self, p1, p2):
        return sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    
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
        collision_position = Vector(x=p_meteor.x + v_meteor.x * cos(theta), y=p_meteor.y + v_meteor.y * sin(theta))
        return collision_position
    
    def compute_target_angle(self, p_meteor, v_meteor, p_rocket, v_rocket):

        a = (p_rocket.y - p_meteor.y) / (p_rocket.x - p_meteor.x)
        b = (a * v_meteor.x - v_meteor.y) / v_rocket

        c = a**2 - b**2 + 1
        if c < 0:
            return None
        theta1 = 2*atan((sqrt(c) - 1)/(a + b))
        theta2 = -2*atan((sqrt(c) - 1)/(a + b))
                
        if -pi/2 < theta1 < pi/2:
            angle = theta1
        # elif -pi/2 < theta2 < pi/2:
        #     angle = theta2
        else:
            return None 
        
        return degrees(angle)
    
    def is_inside_frame(self, meteor_position, world_width, world_height, cannon_position):
        if not (0 <= meteor_position.x <= world_width and 0 <= meteor_position.y <= world_height):
            return False
        
        if meteor_position.x < cannon_position.x:
            return False
        
        return 0 <= meteor_position.x <= world_width and 0 <= meteor_position.y <= world_height
    
    def score_meteor(self, meteor, position, world_width, world_height):
        distance_score = 1 / self.distance(meteor.position, position)
        size_score = {
            MeteorType.Large: 1,
            MeteorType.Medium: 2,
            MeteorType.Small: 3 }[meteor.meteorType]

        
        priority_multiplier = 2 if self.is_inside_priority_frame(meteor.position, world_width, world_height) else 1
        
        return distance_score * size_score * priority_multiplier
        
    def is_inside_priority_frame(self, meteor_position, world_width, world_height, priority_percentage=0.5):
        frame_width = world_width * priority_percentage
        frame_height = world_height * priority_percentage
        frame_left = (world_width - frame_width) / 2
        frame_top = (world_height - frame_height) / 2
        frame_right = frame_left + frame_width
        frame_bottom = frame_top + frame_height

    

        return frame_left <= meteor_position.x <= frame_right and frame_top <= meteor_position.y <= frame_bottom
