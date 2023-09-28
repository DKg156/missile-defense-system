"""The Python implementation of the GRPC missile defence system."""

from threading import Thread, Lock
import logging
import random
import grpc
import missiledefence_pb2
import missiledefence_pb2_grpc
from datetime import datetime as dt

# Create and configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh_formatter = logging.Formatter("%(asctime)s %(message)s")
ch_formatter = logging.Formatter("%(message)s")

start_time = dt.now().strftime("%Y-%m-%d %H_%M_%S")

# File handler to output the log to file
fh = logging.FileHandler(f'logs\soldier_{start_time}.log', mode='w', encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)

# Console handler to output the log to console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(ch_formatter)
logger.addHandler(ch)

missile_details = {
    "M1": {"radius": 1},
    "M2": {"radius": 2},
    "M3": {"radius": 3},
    "M4": {"radius": 4},
}

# commander_url="192.168.199.59:50050"
commander_url="localhost:50050"

layout_updates = 0

# A simple mutex lock which helps to execute a block of code without interference from parallel threads (if needed)
lock = Lock()

class Soldier():

    def __init__(self, sid, position, speed):
        self.sid = sid
        self.position = position
        self.speed = speed
        self.is_commander = False
        self.is_alive = True

    # Ping commander with READY, respond to missile, move soldier, update status and call elect commander in between (if needed)
    def run(self):
        # Ping commander with READY, response will include if the current soldier has to become the first commander
        response = self.send_soldier_ready()

        # If the current soldier has to be elected as the first commander, send election request.
        if response.soldier_id == self.sid:
            logger.info(f"electing commander.. {response.soldier_id}")
            self.request_elect_commander(self.sid)
            return
        
        i = 0
        # Establish gRPC Server streaming
        with grpc.insecure_channel(
            commander_url
        ) as channel:
            stub = missiledefence_pb2_grpc.CommanderStub(channel)
            approaching_missiles = stub.missile_approaching(
                missiledefence_pb2.SoldierFilter(soldier_id=self.sid)
            )
        
            for missile in approaching_missiles:
                # Update the current soldier's layout to match the layout sent by commander after his movement
                with lock:
                    global layout, layout_updates
                    if layout_updates == i:
                        layout = []
                        for layoutRow in missile.layout:
                            layout.append(list(layoutRow.row))
                        logger.info(f"soldier {self.sid} updating layout for missile {i+1}")
                        layout_updates += 1

                # Move soldier (if possible)
                self.take_shelter(
                    missile.missile.position, missile.missile.time, missile.missile.type
                )

                '''
                Update ALIVE status and position after movement (if any)
                If the current soldier is alive, but the commander is dead by this time,
                Commander MIGHT ask the current soldier to be the new commander
                '''
                logger.info("Requesting status update")
                response = self.status(self.sid)

                # If the current soldier has been asked to become new commander, send election_request
                if response.new_commander_id != -1 and self.sid == response.new_commander_id:
                    logger.info(f"Commander dead, requesting to elect soldier {self.sid} as commander")
                    response = self.request_elect_commander(self.sid)
                    break
                if self.is_alive == False:
                    logger.info(f"Soldier {self.sid} dead..")

                logger.info(f"Requesting next missile detail for soldier {self.sid}")
                i+=1

    def send_soldier_ready(self):
        with grpc.insecure_channel(
            commander_url
        ) as channel:
            stub = missiledefence_pb2_grpc.CommanderStub(channel)
            response: missiledefence_pb2.NewCommanderFilter = stub.soldier_ready(
                missiledefence_pb2.ConnectionRequest (
                        soldier_id=self.sid, 
                        position=self.position, 
                        no_of_soldiers=M,
                        warzone_size=N
                    )
            )
        # logger.info(f"Sent soldier_ready of soldier {self.sid}")
        return response

    def request_elect_commander(self, new_commander_id):
        self.is_commander=True
        with grpc.insecure_channel(
            commander_url
        ) as channel:
            stub = missiledefence_pb2_grpc.CommanderStub(channel)

            # The below election request contains the details of the current soldier which will be updated in commander
            # Since the current soldier instance will stop from here and resume from commander side
            stub.elect_commander(
                missiledefence_pb2.NewCommanderDetails(soldier_id=new_commander_id, position=self.position, speed=self.speed)
            )
    
    def status(self, soldier_id):
        if soldier_id == self.sid:
            with grpc.insecure_channel(
                commander_url
            ) as channel:
                stub = missiledefence_pb2_grpc.CommanderStub(channel)
                response: missiledefence_pb2.NewCommanderFilter = stub.status(
                    missiledefence_pb2.WasHit(soldier_id=self.sid, is_alive=self.is_alive, position=self.position)
                )
        return response

    def move_soldier(self, selected_movement, no_of_moves):
        old_x = self.position[0]
        old_y = self.position[1]

        # Update position according to the randomly chosen direction and number of moves
        if selected_movement == "left":
            self.position[1] = old_y - no_of_moves
        elif selected_movement == "right":
            self.position[1] = old_y + no_of_moves
        elif selected_movement == "up":
            self.position[0] = old_x - no_of_moves
        elif selected_movement == "down":
            self.position[0] = old_x + no_of_moves
        elif selected_movement == "left_up":
            self.position[0] = old_x - no_of_moves
            self.position[1] = old_y - no_of_moves
        elif selected_movement == "left_down":
            self.position[0] = old_x + no_of_moves
            self.position[1] = old_y - no_of_moves
        elif selected_movement == "right_up":
            self.position[0] = old_x - no_of_moves
            self.position[1] = old_y + no_of_moves
        else:  # right_down
            self.position[0] = old_x + no_of_moves
            self.position[1] = old_y + no_of_moves

        # Check if new position is going out of war zone boundary. If so, reset position and return FALSE.
        if (
            self.position[0] <= 0
            or self.position[1] <= 0
            or self.position[0] > len(layout)
            or self.position[1] > len(layout[0])
            or layout[self.position[0]-1][self.position[1]-1] != 0
        ):
            self.position[0] = old_x
            self.position[1] = old_y
            return False
        layout[old_x-1][old_y-1] = 0
        layout[self.position[0]-1][self.position[1]-1] = self.sid
        return True

    def take_shelter(self, missile_position, time, missile_type):
        # Print current missile details
        logger.info("Time: {0}".format(time))
        logger.info("Missile type: {0}".format(missile_type))
        rad = missile_details[missile_type]["radius"] - 1
        logger.info("Radius: {0}".format(rad+1))

        # Calculate red zone using missile drop location and radius
        i_start = missile_position[0] - rad
        i_end = missile_position[0] + rad
        j_start = missile_position[1] - rad
        j_end = missile_position[1] + rad

        has_moved = False

        # If current soldier within red zone, try to move
        if (
            i_start <= self.position[0] <= i_end
            and j_start <= self.position[1] <= j_end
        ):
            movements = {}
            # Calculate basic movements - left, right, up down
            movements["left"] = (self.position[1] - j_start) + 1
            movements["right"] = (j_end - self.position[1]) + 1
            movements["up"] = (self.position[0] - i_start) + 1
            movements["down"] = (i_end - self.position[0]) + 1

            # Deduce diagonal movements from basic movements
            movements["left_up"] = min(movements["left"], movements["up"])
            movements["left_down"] = min(movements["left"], movements["down"])
            movements["right_up"] = min(movements["right"], movements["up"])
            movements["right_down"] = min(movements["right"], movements["down"])

            while len(movements) > 0 and not has_moved:
                # Find the minimum of all the above calculated movements
                min_move_calc = min(movements.values())

                # Compare the above result with max speed of the soldier,
                # If speed is lesser than what is needed, soldier can't escape the read zone (DEAD)
                if self.speed >= min_move_calc:
                    # Choose all possible direction where movement can be made with selected min no of moves
                    possible_movements = [
                        key for key in movements if movements[key] == min_move_calc
                    ]
                    selected_movement = random.choice(possible_movements)

                    # Try to move as long as there are possible movements
                    while (
                        len(possible_movements) != 0
                        and has_moved != True
                    ):
                        selected_movement = random.choice(possible_movements)
                        has_moved = self.move_soldier(selected_movement, min_move_calc)
                        if has_moved==False:
                            del movements[selected_movement]
                            possible_movements.remove(selected_movement)

                    if len(movements) == 0 and not has_moved:
                        layout[self.position[0]-1][self.position[1]-1] = 0
                        self.is_alive = False
                        break
                else:
                    self.is_alive = False
                    break
                
            # If soldier dead, make soldier position 0 in layout
            if self.is_alive == False:
                layout[self.position[0] - 1][self.position[1] - 1] = 0
                if self.is_commander == True:
                    self.is_commander = False
                    
        logger.info(f"has_moved: {has_moved}, New position of soldier {self.sid}: {self.position}...")



def take_inputs():
    global N,M,S,layout

    N = int(input("Please enter N (where NxN is the size of war zone): "))

    while True:
        M = int(input("Please enter number of soldiers (M): "))
        if M<=(N*N):
            break
    
    soldierwisePositions = [[-1,-1] for x in range(M)]
    layout = [[0 for x in range(N)] for y in range(N)]

    logger.info("Note: Warzone indexing start from [1,1] for below inputs...")
    for i in range(M):
        while True:
            pos_x = int(input(f"Enter row of soldier {i+1}: "))
            pos_y = int(input(f"Enter col of soldier {i+1}: "))
            logger.info("")
            if pos_x<=len(layout) and pos_y<=len(layout[0]) and layout[pos_x-1][pos_y-1]==0:
                soldierwisePositions[i][0]=pos_x
                soldierwisePositions[i][1]=pos_y
                break

        layout[pos_x-1][pos_y-1] = i+1

    speedList = input("Please enter speed of all soldiers separated by commas (Si): ").split(',')
    S = [int(x) for x in speedList]
    return soldierwisePositions

def start_soldier(sid, position, speed):
    soldier = Soldier(sid, position, speed)
    soldier.run()

if __name__ == "__main__":
    # Taking hyperparameters N,M,Si and soldier positions as inputs from user (T and t will be given at commander site)
    soldierwisePositions = take_inputs()
    threads = []
    # Creating one thread per soldier
    for i in range(M):
        threads.append(Thread(target=start_soldier, args=(i+1, soldierwisePositions[i], S[i])))

    # Starting all the threads one by one
    for t in threads:
        t.start()
    
    # Waiting for all threads to finish
    for t in threads:
        t.join()

