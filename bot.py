from typing import Optional

from game_message import *
from actions import *
from math import sqrt, cos, sin, radians
import copy
import numpy as np
from overengineered_weight_calculator import VectorField, WeightCalculator


class Collision:
    def __init__(self, rocket: Projectile, meteor: Meteor, time: float):
        self.rocket: Projectile = rocket
        self.meteor: Meteor = meteor
        self.time: float = time


class Shot:
    def __init__(self, id: Projectile, target: Meteor, time: float, reason: str):
        self.rocket_id: int = id
        self.target: Meteor = target
        self.time: float = time
        self.reason: str = reason


class Bot:
    def __init__(self):
        self.vector_field: Optional[VectorField] = None
        self.weight_calculator: Optional[WeightCalculator] = None
        self.game_bounds: list[int] = []
        self.target_queue: list[Meteor] = []
        self.pending_collisions: list[Collision] = []
        self.actual_collisions: list[Collision] = []
        self.shot_rockets: list[Shot] = []
        self.reason = ""
        self.large_meteor_uncertainty: float = 0.3
        self.medium_meteor_uncertainty: float = 0.6
        self.small_meteor_uncertainty: float = 1.0
        print("Initializing VAUL domination...")

    def get_next_move(self, game_message: GameMessage) -> list[LookAtAction | RotateAction | ShootAction]:
        # print(f"Score: {game_message.score}")

        if game_message.tick == 999:
            print(f"Shot {len(self.shot_rockets)} rockets")
            print(f"Hit {len(self.actual_collisions)} meteors")
            self.print_missed_shots()

        if not self.game_bounds:
            self.game_bounds = [
                game_message.cannon.position.x + 10,
                game_message.constants.world.width,
                0,
                game_message.constants.world.height]

        if self.vector_field is None:
            cannon_position = (game_message.cannon.position.x, game_message.cannon.position.y)
            edge_point = (game_message.constants.world.width, game_message.constants.world.height)
            self.vector_field = VectorField(cannon_position=cannon_position, edge_point=edge_point)
            self.weight_calculator = WeightCalculator(self.vector_field)

        self.update_pending_collisions(game_message)
        self.update_actual_collisions(game_message)
        self.update_shot_rockets(game_message)

        # If cannon is in cooldown, we can't do anything
        if game_message.cannon.cooldown > 0:
            return []

        # Targetting a meteor
        meteors_collisions: list[Meteor] = self.compute_meteors_collisions(game_message)
        target_meteor: Meteor = self.select_target_meteor(meteors_collisions, game_message)
        if target_meteor is None:
            return []
        elif target_meteor.meteorType in [MeteorType.Large, MeteorType.Medium] and self.reason == "Score":
            collision_time: float = self.estimate_collision_time(target_meteor, game_message.tick, game_message)
            self.target_child_meteors(target_meteor, collision_time, game_message)

        # print(f"Shooting at {target_meteor.id} for {self.reason}. (Queued: {len(self.target_queue)}, Pending: {[collision.meteor.id for collision in self.pending_collisions]})")

        # Moving the cannon to hit the targetted meteor
        self.shot_rockets.append(Shot(id=-1, target=target_meteor, time=game_message.tick, reason=self.reason))
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
                print(
                    f'Skipping collision computation for {meteor.meteorType} at position ({round(meteor.position.x)},{round(meteor.position.y)})')
        return meteors_collisions

    def select_target_meteor(self, meteors: list[Meteor], game_message: GameMessage) -> Meteor:
        pending_meteors = [collision.meteor.id for collision in self.pending_collisions]
        candidate_meteors: list[Meteor] = [meteor for meteor in meteors
                                           if meteor.id not in pending_meteors
                                           and self.is_inside_bounds(meteor.position)]
        small_meteors: list[Meteor] = [meteor for meteor in candidate_meteors if meteor.meteorType == MeteorType.Small]
        medium_meteors: list[Meteor] = [meteor for meteor in candidate_meteors if
                                        meteor.meteorType == MeteorType.Medium]
        large_meteors: list[Meteor] = [meteor for meteor in candidate_meteors if meteor.meteorType == MeteorType.Large]
        candidate_meteors = small_meteors if small_meteors else medium_meteors if medium_meteors else large_meteors

        if self.target_queue and not small_meteors:
            self.reason = "Queue"
            return self.target_queue.pop(0)
        else:
            self.reason = "Score"
            self.target_queue = []
            scores = self.score_meteors(candidate_meteors, game_message)
            sorted_candidates: list[Meteor] = [meteor for _, meteor in
                                               sorted(zip(scores, candidate_meteors), key=lambda x: (x[0] is None, x[0]), reverse=True)
]
            return sorted_candidates[0] if sorted_candidates else None

    def score_meteors(self, meteors: List[Meteor], game_message: GameMessage) -> List[float]:
        scores: List[float] = []

        for meteor in meteors:
            # Extract meteor properties
            x = meteor.position.x
            y = meteor.position.y
            velocity_x = meteor.velocity.x
            velocity_y = meteor.velocity.y
            type_meteor = meteor.meteorType.value

            # Calculate weight using WeightCalculator
            score = self.weight_calculator.compute_weight(type_meteor, x, y, velocity_x, velocity_y)
            print(f"Score for {meteor.meteorType} at ({round(x)},{round(y)}): {score}")
            if score is None:
                score = 0  # or any other default value)
            print(score)
            scores.append(score)

        return scores

    def estimate_collision_time(self, target_meteor: Meteor, launch_time: float, game_message: GameMessage) -> float:
        p_rocket: Vector = game_message.cannon.position
        v_rocket: float = game_message.constants.rockets.speed
        collision_point: Vector = target_meteor.position
        return launch_time + self.distance(p_rocket, collision_point) / v_rocket

    def target_child_meteors(self, parent_meteor: Meteor, parent_collision_time: float,
                             game_message: GameMessage) -> None:

        for child in game_message.constants.meteorInfos[parent_meteor.meteorType].explodesInto:
            # Next rocket will launch after all queued rockets
            launch_time = game_message.tick + (len(self.target_queue) + 1) * game_message.constants.cannonCooldownTicks

            meteor_size: float = game_message.constants.meteorInfos[child.meteorType].size
            child_meteor: Meteor = Meteor(id=-1, meteorType=child.meteorType, position=Vector(0, 0),
                                          velocity=Vector(0, 0), size=meteor_size)
            split_angle: float = radians(child.approximateAngle)
            parent_speed: float = np.linalg.norm([parent_meteor.velocity.x, parent_meteor.velocity.y])
            speed_ratio: float = game_message.constants.meteorInfos[child.meteorType].approximateSpeed / parent_speed
            child_meteor.velocity = Vector(
                x=speed_ratio * (
                            cos(split_angle) * parent_meteor.velocity.x - sin(split_angle) * parent_meteor.velocity.y),
                y=speed_ratio * (
                            sin(split_angle) * parent_meteor.velocity.x + cos(split_angle) * parent_meteor.velocity.y)
            )

            child_meteor.position = self.get_collision_position(parent_meteor.position, child_meteor.velocity,
                                                                game_message.cannon.position,
                                                                game_message.constants.rockets.speed,
                                                                parent_collision_time, launch_time)
            if child_meteor.position is not None \
                    and self.is_inside_bounds(child_meteor.position) \
                    and self.uncertainty_check(child_meteor, parent_meteor.position, game_message):
                self.target_queue.append(child_meteor)
                print(
                    f'Added {child_meteor.meteorType} meteor colliding at position ({round(child_meteor.position.x)},{round(child_meteor.position.y)}) to target_queue')
                child_collision_time: float = self.estimate_collision_time(child_meteor, launch_time, game_message)
                self.target_child_meteors(child_meteor, child_collision_time, game_message)

    def get_collision_position(self, p0_meteor: Vector, v_meteor: Vector, p0_rocket: Vector, v_rocket: float,
                               t0_meteor: float = 0.0, t0_rocket: float = 0.0) -> [Vector | None]:

        rocket_lead: float = t0_meteor - t0_rocket
        if rocket_lead < 0: return None
        delta_t: float = 0.0
        rate: float = 0.02
        error: float = 1000.0
        iteration: int = 0
        while abs(error) > 0.1 and iteration < 100:
            position = Vector(x=p0_meteor.x + delta_t * v_meteor.x, y=p0_meteor.y + delta_t * v_meteor.y)
            rocket_travel_distance = (rocket_lead + delta_t) * v_rocket
            cannon_target_distance = self.distance(position, p0_rocket)
            error = cannon_target_distance - rocket_travel_distance
            delta_t += rate * error
            iteration += 1

        if iteration == 100:
            return None
        else:
            return position

    def is_inside_bounds(self, position) -> bool:
        return (self.game_bounds[0] < position.x < self.game_bounds[1] and \
                self.game_bounds[2] < position.y < self.game_bounds[3])

    def uncertainty_check(self, meteor: Meteor, initial_position: Vector, game_message: GameMessage) -> bool:

        speed_uncertainty = self.large_meteor_uncertainty if meteor.meteorType == MeteorType.Large \
            else self.medium_meteor_uncertainty if meteor.meteorType == MeteorType.Medium \
            else self.small_meteor_uncertainty
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
        return sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    def update_pending_collisions(self, game_message: GameMessage) -> None:
        for rocket in game_message.rockets:
            for meteor in game_message.meteors:
                will_collide, mintime = self.will_collide(rocket, meteor)
                if will_collide and not any(
                        (collision.rocket.id == rocket.id and collision.meteor.id == meteor.id) for collision in
                        self.pending_collisions):
                    self.pending_collisions.append(Collision(rocket, meteor, game_message.tick + mintime))
        self.remove_duplicate_collisions()
        self.remove_old_collisions(game_message)

    def update_actual_collisions(self, game_message: GameMessage) -> None:
        for collision in self.pending_collisions:
            if collision.time - game_message.tick < 5 \
                    and collision.rocket.id not in [collision.rocket.id for collision in self.actual_collisions] \
                    and collision.meteor.id not in [collision.meteor.id for collision in self.actual_collisions]:
                self.actual_collisions.append(collision)

    def will_collide(self, rocket: Projectile, meteor: Meteor) -> bool:
        # Check if rocket and meteor will collide and when
        r_vel_x, r_vel_y = rocket.velocity.x, rocket.velocity.y
        m_vel_x, m_vel_y = meteor.velocity.x, meteor.velocity.y
        r_pos_x, r_pos_y = rocket.position.x, rocket.position.y
        m_pos_x, m_pos_y = meteor.position.x, meteor.position.y
        mintime = -(r_pos_x * r_vel_x - r_vel_x * m_pos_x - (
                    r_pos_x - m_pos_x) * m_vel_x + r_pos_y * r_vel_y - r_vel_y * m_pos_y - (
                                r_pos_y - m_pos_y) * m_vel_y) / \
                  (
                              r_vel_x ** 2 - 2 * r_vel_x * m_vel_x + m_vel_x ** 2 + r_vel_y ** 2 - 2 * r_vel_y * m_vel_y + m_vel_y ** 2)
        mindist = sqrt((mintime * (r_vel_x - m_vel_x) + r_pos_x - m_pos_x) ** 2 + (
                    mintime * (r_vel_y - m_vel_y) + r_pos_y - m_pos_y) ** 2)
        will_collide = mindist < meteor.size + rocket.size
        return will_collide, mintime

    def remove_duplicate_collisions(self) -> None:
        # Remove collisions with same rocket or meteor but later time
        self.pending_collisions = [collision for i, collision in enumerate(self.pending_collisions)
                                   if not any(
                (collision.rocket.id == other.rocket.id or collision.meteor.id == other.meteor.id)
                and collision.time > other.time for other in self.pending_collisions)]

    def remove_old_collisions(self, game_message: GameMessage) -> None:
        # Check if rocket id and meteor id are still in the game
        self.pending_collisions = [collision for collision in self.pending_collisions
                                   if collision.rocket.id in [rocket.id for rocket in game_message.rockets]
                                   and collision.meteor.id in [meteor.id for meteor in game_message.meteors]]

    def update_shot_rockets(self, game_message: GameMessage) -> None:
        for shot in self.shot_rockets:
            if shot.rocket_id == -1 and game_message.rockets:
                shot.rocket_id = game_message.rockets[-1].id
            elif shot.target.id == -1 and shot.rocket_id in [collision.rocket.id for collision in
                                                             self.actual_collisions]:
                shot.target.id = \
                [collision.meteor.id for collision in self.actual_collisions if collision.rocket.id == shot.rocket_id][
                    0]

    def print_missed_shots(self) -> None:
        missed_shots: list[Shot] = [shot for shot in self.shot_rockets
                                    if (shot.rocket_id, shot.target.id)
                                    not in [(collision.rocket.id, collision.meteor.id)
                                            for collision in self.actual_collisions]]
        print(f"Missed shots: {len(missed_shots)}")
        for shot in missed_shots:
            if shot.rocket_id in [collision.rocket.id for collision in self.actual_collisions]:
                actual_hit = \
                [collision.meteor.id for collision in self.actual_collisions if collision.rocket.id == shot.rocket_id][
                    0]
                print(
                    f"[{shot.time}] Rocket {shot.rocket_id} aimed at meteor {shot.target.id} of type {shot.target.meteorType}, but hit {actual_hit} instead. ({shot.reason})")
            else:
                print(
                    f"[{shot.time}] Rocket {shot.rocket_id} aimed at meteor {shot.target.id} of type {shot.target.meteorType}, but simply missed. ({shot.reason})")
