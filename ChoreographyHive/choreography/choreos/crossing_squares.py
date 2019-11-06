import numpy as np

from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.game_state_util import GameState, CarState, Physics, Vector3, Rotator, BallState
from rlbot.utils.structures.game_interface import GameInterface

from choreography.choreography import Choreography
from choreography.drone import slow_to_pos
from choreography.group_step import BlindBehaviorStep, DroneListStep, StepResult, PerDroneStep


class CrossingSquares(Choreography):
    """
    A simple choreography where two squares of bots cross. Requires 32 bots.
    """

    def __init__(self, game_interface: GameInterface):
        super().__init__()
        self.game_interface = game_interface

    def generate_sequence(self):
        self.sequence.clear()

        pause_time = 1.0

        self.sequence.append(DroneListStep(self.hide_ball))
        self.sequence.append(DroneListStep(self.make_squares))
        self.sequence.append(DroneListStep(self.delayed_start))
        self.sequence.append(DroneListStep(self.interweave))
        self.sequence.append(BlindBehaviorStep(SimpleControllerState(), pause_time))

    @staticmethod
    def get_num_bots() -> int:
        return 32

        
    def hide_ball(self, packet, drones, start_time) -> StepResult:
        """
        Places the ball above the roof of the arena to keep it out of the way.
        """
        self.game_interface.set_game_state(GameState(ball=BallState(physics=Physics(
            location=Vector3(0, 0, 3000),
            velocity=Vector3(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0)))))
        return StepResult(finished=True)

        
    def line_up(self, packet, drones, start_time) -> StepResult:
        """
        Puts all the cars in a tidy line, very close together.
        """
        start_x = -2000
        y_increment = 100
        start_y = -len(drones) * y_increment / 2
        start_z = 40
        car_states = {}
        for drone in drones:
            car_states[drone.index] = CarState(
                Physics(location=Vector3(start_x, start_y + drone.index * y_increment, start_z),
                        velocity=Vector3(0, 0, 0),
                        rotation=Rotator(0, 0, 0)))
        self.game_interface.set_game_state(GameState(cars=car_states))
        return StepResult(finished=True)


    def make_squares(self, packet, drones, start_time) -> StepResult:
        """
        Separates all the bots into two squares, facing each other.
        """
        self.squareA = drones[:16]
        self.squareB = drones[16:]

        spacing = 250
        y_offset = 2550
        x_offset = 3 * spacing / 2

        car_states = {}
        for i, drone in enumerate(self.squareA):
            car_states[drone.index] = CarState(
                Physics(location=Vector3(x_offset - spacing*(i % 4), -y_offset - spacing*(i // 4), 20),
                        velocity=Vector3(0, 0, 0),
                        rotation=Rotator(0, np.pi/2, 0)))
                        
        for i, drone in enumerate(self.squareB):
            car_states[drone.index] = CarState(
                Physics(location=Vector3(-x_offset + spacing*(i % 4), y_offset + spacing*(i // 4), 20),
                        velocity=Vector3(0, 0, 0),
                        rotation=Rotator(0, -np.pi/2, 0)))

        self.game_interface.set_game_state(GameState(cars=car_states))
        return StepResult(finished=True)

        
    def delayed_start(self, packet, drones, start_time) -> StepResult:
        """
        Spreads bots out by delaying the start of each row.
        """
        elapsed = packet.game_info.seconds_elapsed - start_time

        for drone in drones:
            throttle_start = (drone.index % 16 // 4) * 0.9
            drone.ctrl = SimpleControllerState()

            if throttle_start < elapsed:
                # Speed controller.
                vel = np.linalg.norm(drone.vel*np.array([1,1,0]))
                drone.ctrl.throttle = 0 if vel > 650 else 0.7

        return StepResult(finished=elapsed > 3.6)


    def interweave(self, packet, drones, start_time) -> StepResult:
        """
        Make bots jump alternating such that they jump over each other.
        """
        elapsed = packet.game_info.seconds_elapsed - start_time
        start = 0.0
        hold = 0.05
        buffer = 0.65

        for drone in drones:
            drone.ctrl = SimpleControllerState()

            # Speed controller.
            vel = np.linalg.norm(drone.vel*np.array([1,1,0]))
            drone.ctrl.throttle = 0 if vel > 650 else 0.7

            if (drone.index % 2 == 0):
                if start < elapsed < start+hold:
                    drone.ctrl.jump = True
                elif start+2*buffer < elapsed < start+2*buffer+hold:
                    drone.ctrl.jump = True
                elif start+4*buffer < elapsed < start+4*buffer+hold:
                    drone.ctrl.jump = True
                elif start+6*buffer < elapsed < start+6*buffer+hold:
                    drone.ctrl.jump = True
            else:
                if start+buffer < elapsed < start+buffer+hold:
                    drone.ctrl.jump = True
                elif start+3*buffer < elapsed < start+3*buffer+hold:
                    drone.ctrl.jump = True
                elif start+5*buffer < elapsed < start+5*buffer+hold:
                    drone.ctrl.jump = True
        
        return StepResult(finished=elapsed > start+8*buffer)

