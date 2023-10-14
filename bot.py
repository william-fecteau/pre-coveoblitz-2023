from game_message import *
from actions import *
from math import atan, sqrt, cos, sin, radians
import copy

class Bot:
    def __init__(self):
        self.targetted_meteor_ids: list[int] = []
        self.child_targets: list[Meteor] = []
        self.next_launch = 0
        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage) -> list[LookAtAction | RotateAction | ShootAction]:
        #print(f"Score: {game_message.score}")

        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []

        # Targetting a meteor
        if self.child_targets:
            target_meteor: Meteor = self.child_targets.pop(0)
        else:
            meteors_collisions: list[Meteor] = self.compute_meteors_collisions(game_message)
            target_meteor: Meteor = self.select_target_meteor(meteors_collisions, game_message)
            if target_meteor is None:
                return []
            elif target_meteor.meteorType in [MeteorType.Large, MeteorType.Medium]:
                collision_time: float = self.estimate_collision_time(target_meteor, game_message.tick, game_message)
                #self.check_for_child_targets(target_meteor, game_message.tick, collision_time, game_message)
        
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
            collision_point = self.get_collision_position(meteor.position, meteor.velocity, p_rocket, v_rocket)
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
    

    def estimate_collision_time(self, target_meteor: Meteor, launch_time: float, game_message: GameMessage) -> float:
        p_rocket: Vector = game_message.cannon.position
        v_rocket: float = game_message.constants.rockets.speed
        collision_point: Vector = target_meteor.position
        return launch_time + self.distance(p_rocket, collision_point) / v_rocket
    

    def check_for_child_targets(self, target_meteor: Meteor, launch_time: float, split_time: float, game_message: GameMessage) -> None:

        launch_time += game_message.constants.cannonCooldownTicks

        for child in game_message.constants.meteorInfos[target_meteor.meteorType].explodesInto:
            child_meteor: Meteor = Meteor(id=-1, meteorType=child.meteorType, position=Vector(0,0), velocity=Vector(0,0), size=0)
            angle: float = radians(child.approximateAngle)
            speed_ratio: float = game_message.constants.meteorInfos[child.meteorType].approximateSpeed / game_message.constants.meteorInfos[target_meteor.meteorType].approximateSpeed
            child_meteor.velocity = Vector(
                x = speed_ratio * (cos(angle)*target_meteor.velocity.x + sin(angle)*target_meteor.velocity.x), 
                y = speed_ratio * (cos(angle)*target_meteor.velocity.y - sin(angle)*target_meteor.velocity.y)
            )
            # position_at_next_launch: Vector = Vector(
            #     x = target_meteor.position.x + child_meteor.velocity.x * (launch_time - split_time),
            #     y = child_meteor.velocity.y * (launch_time - split_time) + target_meteor.position.y
            # )
            child_meteor.position = self.get_collision_position_child(target_meteor.position, child_meteor.velocity, game_message.cannon.position, game_message.constants.rockets.speed, split_time, launch_time)
            child_collision_time: float = self.estimate_collision_time(child_meteor, launch_time, game_message)
            if self.is_inside_bounds(child_meteor.position, [game_message.cannon.position.x, game_message.constants.world.width, 0, game_message.constants.world.height]):
                self.child_targets.append(child_meteor)
                launch_time += game_message.constants.cannonCooldownTicks
                self.check_for_child_targets(child_meteor, launch_time, child_collision_time, game_message)


    def update_targeted_ids(self, target_id, meteors: list[Meteor]) -> None:
        for id in self.targetted_meteor_ids:
            if id not in [meteor.id for meteor in meteors]:
                self.targetted_meteor_ids.remove(id)
        if target_id not in self.targetted_meteor_ids:
            self.targetted_meteor_ids.append(target_id)


    def get_collision_position(self, p_meteor: Vector, v_meteor: Vector, p_rocket: Vector, v_rocket: float) -> (Vector, float):
        # a,b,c are bad names but used to simplify the equations
        a: float = (p_rocket.y - p_meteor.y) / (p_rocket.x - p_meteor.x)
        b: float = (a * v_meteor.x - v_meteor.y) / v_rocket
        c: float = a**2 - b**2 + 1
        if c < 0:
            return None
        theta: float = 2*atan((sqrt(c) - 1)/(a + b)) 
        delta_t: float = (p_rocket.x - p_meteor.x) / (v_meteor.x - v_rocket * cos(theta))
        collision_point: Vector = Vector(x=p_meteor.x + delta_t * v_meteor.x, y=p_meteor.y + delta_t * v_meteor.y)
        return collision_point
    

    def get_collision_position_child(self, p0_meteor: Vector, v_meteor: Vector, p0_rocket: Vector, v_rocket: float, 
                                     t0_meteor: float, t0_rocket: float) -> Vector:

        a = p0_rocket.y - p0_meteor.y + t0_meteor*v_meteor.y
        b = p0_rocket.x - p0_meteor.x + t0_meteor*v_meteor.x
        vr = v_rocket
        t1 = t0_rocket
        vmx = v_meteor.x
        vmy = v_meteor.y
        c = -a**2*vmx**2 + a**2*vr**2 + 2*a*b*vmx*vmy - 2*a*t1*vmy*vr**2 - b**2*vmy**2 + b**2*vr**2 - 2*b*t1*vmx*vr**2 + t1**2*vmx**2*vr**2 + t1**2*vmy**2*vr**2
        if c < 0:
            return None
        theta: float = 2*atan((-b*vr + t1*vmx*vr + sqrt(c)) / (a*vmx + a*vr - b*vmy - t1*vmy*vr))
        tc2: float = (b - t1*vr*cos(theta)) / (vmx - vr*cos(theta))
        delta_t: float = tc2 - t0_meteor
        collision_point: Vector = Vector(x=p0_meteor.x + delta_t * v_meteor.x, y=p0_meteor.y + delta_t * v_meteor.y)
        return collision_point
    

    def is_inside_bounds(self, position, bounds) -> bool:
        return (bounds[0] <= position.x <= bounds[1] and \
                bounds[2] <= position.y <= bounds[3])


    def distance(self, p1, p2) -> float:
        return sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)