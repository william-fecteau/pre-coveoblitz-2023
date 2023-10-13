from game_message import *
from actions import *
from math import atan, sqrt, pi, degrees
class Bot:
    def __init__(self):
        self.targetted_meteor_ids: list[int] = []
        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage):
        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []

        # Targetting a meteor
        target_meteor: Meteor = self.select_target_meteor(game_message.meteors, game_message)
        if target_meteor is None:
            fallback_move_action = self.get_fallback_strategy_action(game_message)
            return [fallback_move_action, ShootAction()] 

        # Moving the cannon to hit the targetted meteor
        cannon_move_action = self.get_cannon_move_action(target_meteor, game_message)
        if cannon_move_action is None:
            fallback_move_action = self.get_fallback_strategy_action(game_message)
            return [fallback_move_action, ShootAction()] 

        
        return [
            cannon_move_action,
            ShootAction()
        ]


    def select_target_meteor(self, meteors: list[Meteor], game_message: GameMessage) -> Meteor:
        cannon_position: Vector = game_message.cannon.position

        sorted_meteors: list[Meteor] = sorted(meteors, key=lambda meteor: meteor.position.x)

        buffer_distance: float = 200.0
        min_x_to_shoot: float = cannon_position.x + buffer_distance

        target_meteor: Meteor = None
        for meteor in sorted_meteors:
            if meteor.position.x > min_x_to_shoot and meteor.id not in self.targetted_meteor_ids:
                target_meteor = meteor
                break
        
        if target_meteor is not None:
            self.targetted_meteor_ids.append(target_meteor.id)

        return target_meteor
    

    def get_cannon_move_action(self, target_meteor: Meteor, game_message: GameMessage) -> LookAtAction | RotateAction:
        cannon_position: Vector = game_message.cannon.position
        current_cannon_orientation = game_message.cannon.orientation
        rocket_speed = game_message.constants.rockets.speed
        
        target_angle: float = self.compute_target_angle(target_meteor.position, target_meteor.velocity, cannon_position, rocket_speed)
        if target_angle is None:
            return None

        delta_angle: float = target_angle - current_cannon_orientation

        return RotateAction(angle=delta_angle)


    def compute_target_angle(self, p_meteor: Vector, v_meteor: Vector, p_rocket: Vector, v_rocket: float):
        a = (p_rocket.y - p_meteor.y) / (p_rocket.x - p_meteor.x)
        b = (a * v_meteor.x - v_meteor.y) / v_rocket

        c = a**2 - b**2 + 1
        if c < 0:
            return None
        theta1 = 2*atan((sqrt(c) - 1)/(a + b))
                
        if -pi/2 < theta1 < pi/2:
            angle = theta1
        else:
            return None 
        
        return degrees(angle)
        

    def get_fallback_strategy_action(self, game_message: GameMessage) -> LookAtAction | RotateAction:
        sorted_meteors: list[Meteor] = sorted(game_message.meteors, key=lambda meteor: meteor.position.x)
        
        return LookAtAction(sorted_meteors[0]) 