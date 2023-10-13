from game_message import *
from actions import *
from math import atan, sqrt, pi, degrees
class Bot:
    def __init__(self):
        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage):
        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []

        world_width: int = game_message.constants.world.width
        world_height: int = game_message.constants.world.height
        cannon_position: Vector = game_message.cannon.position

        target_meteor: Meteor = self.select_target_meteor(game_message.meteors, cannon_position, world_width, world_height)
        if target_meteor is None:
            return [] # Maybe fallback to shooting at random meteor

        cannon_move_action = self.get_cannon_move_action(target_meteor, game_message.cannon.position, game_message.constants.rockets.speed, game_message.cannon.orientation)
        if cannon_move_action is None:
            return [] # Maybe fallback to shooting at random meteor

        return [
            cannon_move_action,
            ShootAction()
        ]



    def select_target_meteor(self, meteors: list[Meteor], cannon_position: Vector, world_width: int, world_height: int) -> Meteor:
        sorted_meteors: list[Meteor] = sorted(meteors, key=lambda meteor: meteor.position.x)

        target_meteor = None
        for meteor in sorted_meteors:
            if meteor.position.x > cannon_position.x:
                target_meteor = meteor
                break

        return target_meteor
    

    def get_cannon_move_action(self, target_meteor: Meteor, cannon_position: Vector, rocket_speed: float, current_cannon_orientation: float) -> LookAtAction | RotateAction:
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
        
