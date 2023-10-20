from game_message import *
from actions import *
from math import acos, sqrt, cos, sin, radians, degrees
import copy
import numpy as np

class Bot:
    def __init__(self):
        self.targetted_meteor_ids: list[int] = {}
        self.target_queue: list[Meteor] = []
        self.game_bounds: list[int] = []
        self.large_meteor_uncertainty: float = 0.35
        self.medium_meteor_uncertainty: float = 1.15
        self.small_meteor_uncertainty: float = 1.55
        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage) -> list[LookAtAction | RotateAction | ShootAction]:
        if not self.game_bounds:
            self.game_bounds = [
                game_message.cannon.position.x + 0, 
                game_message.constants.world.width, 
                0, 
                game_message.constants.world.height]

        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []

        print(f'==============================================Tick {game_message.tick}==============================================')
        print(f'Current score: {game_message.score}')

        # Only do child_meteor when its worth it
        child_computation_thresold = game_message.cannon.position.x + game_message.constants.rockets.speed * game_message.constants.cannonCooldownTicks + 100

        # Targetting a meteor
        if self.target_queue:
            target_meteor: Meteor = self.target_queue.pop(0)
            print(f'Popping target queue. {len(self.target_queue)} meteors still in target queue')
        else:
            meteors_collisions: list[Meteor] = self.compute_meteors_collisions(game_message)
            target_meteor: Meteor = self.select_target_meteor(meteors_collisions)
            if target_meteor is None:
                print('self.select_target_meteor returned null. Defaulting to no-op')
                return [] 
            elif target_meteor.meteorType in [MeteorType.Medium, MeteorType.Large] and target_meteor.position.x > child_computation_thresold:
                collision_time: float = self.estimate_collision_time(target_meteor, game_message.tick, game_message)
                self.target_child_meteors(target_meteor, collision_time, game_message)
        

        # Updating the targeted ids
        collision_tick = self.estimate_collision_time(target_meteor, game_message.tick, game_message)
        self.update_targeted_ids(target_meteor.id, collision_tick, game_message)

        # Moving the cannon to hit the targetted meteor   
        print(f'Shooting at {target_meteor.meteorType} meteor at position ({round(target_meteor.position.x)},{round(target_meteor.position.y)})')   
        return [
            LookAtAction(target_meteor.position),
            ShootAction()
        ]
    

    def compute_meteors_collisions(self, game_message: GameMessage) -> list[Meteor]:
        p_rocket: Vector = game_message.cannon.position
        v_rocket: float = game_message.constants.rockets.speed
        meteors_collisions: list[Meteor] = []
        for meteor in game_message.meteors:
            collision_point = self.get_collision_position(meteor.position, meteor.velocity, p_rocket, v_rocket)
            if collision_point is not None:
                meteor_copy: Meteor = copy.deepcopy(meteor)
                meteor_copy.position = collision_point
                meteors_collisions.append(meteor_copy)
            else:
                print(f'Skipping collision computation for {meteor.meteorType} at position ({round(meteor.position.x)},{round(meteor.position.y)})')
        return meteors_collisions
    

    def select_target_meteor(self, meteors: list[Meteor]) -> Meteor:
        reachable_meteors: list[Meteor] = [meteor for meteor in meteors if self.is_inside_bounds(meteor.position)]
        candidate_meteors: list[Meteor] = [meteor for meteor in reachable_meteors if meteor.id not in self.targetted_meteor_ids]
        sorted_candidates: list[Meteor] = sorted(sorted(candidate_meteors, key=lambda meteor: meteor.position.x), key=lambda meteor: meteor.meteorType, reverse=True)
        return sorted_candidates[0] if sorted_candidates else None
    

    def estimate_collision_time(self, target_meteor: Meteor, launch_time: float, game_message: GameMessage) -> float:
        p_rocket: Vector = game_message.cannon.position
        v_rocket: float = game_message.constants.rockets.speed
        collision_point: Vector = target_meteor.position
        return launch_time + self.distance(p_rocket, collision_point) / v_rocket
    

    def target_child_meteors(self, parent_meteor: Meteor, parent_collision_time: float, game_message: GameMessage) -> None:

        for child in game_message.constants.meteorInfos[parent_meteor.meteorType].explodesInto:
            # Next rocket will launch after all queued rockets
            launch_time = game_message.tick + (len(self.target_queue) + 1) * game_message.constants.cannonCooldownTicks
            
            meteor_size: float = game_message.constants.meteorInfos[child.meteorType].size
            child_meteor: Meteor = Meteor(id=-1, meteorType=child.meteorType, position=Vector(0,0), velocity=Vector(0,0), size=meteor_size)
            split_angle: float = radians(child.approximateAngle)
            parent_speed: float = np.linalg.norm([parent_meteor.velocity.x, parent_meteor.velocity.y])
            speed_ratio: float = game_message.constants.meteorInfos[child.meteorType].approximateSpeed / parent_speed
            child_meteor.velocity = Vector(
                x = speed_ratio * (cos(split_angle)*parent_meteor.velocity.x - sin(split_angle)*parent_meteor.velocity.y), 
                y = speed_ratio * (sin(split_angle)*parent_meteor.velocity.x + cos(split_angle)*parent_meteor.velocity.y)
            )
            child_meteor.position = self.get_collision_position(parent_meteor.position, child_meteor.velocity, game_message.cannon.position, 
                                                                        game_message.constants.rockets.speed, parent_collision_time, launch_time)
            if self.is_inside_bounds(child_meteor.position) and self.uncertainty_check(child_meteor, parent_meteor.position, game_message):
                self.target_queue.append(child_meteor)
                print(f'Added {child_meteor.meteorType} meteor colliding at position ({round(child_meteor.position.x)},{round(child_meteor.position.y)}) to target_queue')
                child_collision_time: float = self.estimate_collision_time(child_meteor, launch_time, game_message)
                self.target_child_meteors(child_meteor, child_collision_time, game_message)


    def update_targeted_ids(self, target_id, target_collision_tick: int, game_message: GameMessage) -> None:
        current_tick = game_message.tick
        keys_to_delete = []
        for id, collision_tick in self.targetted_meteor_ids.items():
            if current_tick > collision_tick:
                keys_to_delete.append(id)

        for key in keys_to_delete:
            del self.targetted_meteor_ids[key]

        if target_id not in self.targetted_meteor_ids.keys():
            self.targetted_meteor_ids[target_id] = target_collision_tick


    def get_collision_position(self, p0_meteor: Vector, v_meteor: Vector, p0_rocket: Vector, v_rocket: float, 
                                t0_meteor: float = 0, t0_rocket: float = 0) -> Vector:
        
        rocket_lead: float = t0_meteor - t0_rocket
        delta_t: float = 0.0
        rate: float = 0.02
        error: float = 1000
        while abs(error) > 1.0:
            position = Vector(x=p0_meteor.x + delta_t * v_meteor.x, y=p0_meteor.y + delta_t * v_meteor.y)
            rocket_travel_distance = (rocket_lead + delta_t) * v_rocket
            cannon_target_distance = self.distance(position, p0_rocket)
            error = cannon_target_distance - rocket_travel_distance
            delta_t += rate * error

        return position
    

    def is_inside_bounds(self, position) -> bool:
        return (self.game_bounds[0] <= position.x <= self.game_bounds[1] and \
                self.game_bounds[2] <= position.y <= self.game_bounds[3])
    

    def uncertainty_check(self, meteor: Meteor, initial_position: Vector, game_message: GameMessage) -> bool:

        if meteor.meteorType == MeteorType.Large:
            speed_uncertainty = self.large_meteor_uncertainty
        elif meteor.meteorType == MeteorType.Medium:
            speed_uncertainty = self.medium_meteor_uncertainty
        else:
            speed_uncertainty = self.small_meteor_uncertainty

        distance_to_travel = self.distance(meteor.position, initial_position)
        position_uncertainty = distance_to_travel * speed_uncertainty
        rocket_vector = [meteor.position.x - game_message.cannon.position.x, 
                            meteor.position.y - game_message.cannon.position.y]
        rocket_vector /= np.linalg.norm(rocket_vector)
        meteor_vector = [meteor.velocity.x, meteor.velocity.y]
        meteor_vector /= np.linalg.norm(meteor_vector)
        uncertainty = (1 - abs(np.dot(rocket_vector, meteor_vector))) * position_uncertainty
        return uncertainty < meteor.size + game_message.constants.rockets.size


    def distance(self, p1, p2) -> float:
        return sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    