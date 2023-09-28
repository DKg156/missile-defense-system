"""The Python implementation of the GRPC missile defence system."""

from concurrent import futures
from threading import Lock
import logging
import random
import grpc
import missiledefence_pb2
import missiledefence_pb2_grpc
import google.protobuf.empty_pb2
import time
from datetime import datetime as dt

# Create and configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh_formatter = logging.Formatter("%(asctime)s %(message)s")
ch_formatter = logging.Formatter("%(message)s")

start_time = dt.now().strftime("%Y-%m-%d %H_%M_%S")

# File handler to output the log to file
fh = logging.FileHandler(f'logs\commander_{start_time}.log', mode='w', encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)

# Console handler to output the log to console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(ch_formatter)
logger.addHandler(ch)

commander_port = "50050"

missile_details = {
    "M1": {"radius": 1},
    "M2": {"radius": 2},
    "M3": {"radius": 3},
    "M4": {"radius": 4},
}

# missile_launches = [
#     {"position": [1, 2], "time": 5, "type": "M1", "sent":False},
#     {"position": [1, 1], "time": 10, "type": "M2", "sent":False},
#     {"position": [2, 1], "time": 15, "type": "M3", "sent":False},
#     {"position": [2, 2], "time": 20, "type": "M4", "sent":False},
# ]
missile_launches = []


casuality_count = 0

# A simple mutex lock which helps to execute a block of code without interference from parallel threads (if needed)
lock = Lock()

class Commander(missiledefence_pb2_grpc.CommanderServicer):

    def __init__(self):
        # Attributes of commander as a soldier
        self.sid = -1
        self.position = [-1, -1]
        self.speed = 0
        self.is_alive = True

        self.war_zone_size = 0
        self.no_of_soldiers = 0
        self.layout = []
        self.soldier_details = {}
        self.dead_soldiers = []

        # Attributes to help in synchronization
        self.status_requests_received={}
        self.commander_dead_sent = False
        self.is_war_over = False

        self.soldier_ready_semaphore = 0
        self.initial_layout_semaphore = 0
        self.updated_layout_semaphore = 0
        self.take_shelter_semaphore = 0
        
    # On receiving the FIRST ping from soldiers along with their details,
    # Set the initial values of hyperparameters N,M and layout
    def soldier_ready(self, request, context):
        # logger.info(f"Received status of soldier {request.soldier_id}, position: {request.position}")
        self.no_of_soldiers = request.no_of_soldiers

        self.soldier_details[request.soldier_id] = {
            "position": request.position,
            "is_alive": True
        }
        pos_x = request.position[0]
        pos_y = request.position[1]

        if len(self.layout)==0:
            # If layout has not been set by any other thread, set layout
            self.layout = [[0 for x in range(request.warzone_size)] for y in range(request.warzone_size)]
            self.war_zone_size = request.warzone_size
        with lock:
            self.soldier_ready_semaphore+=1
            if self.soldier_ready_semaphore == 1:
                # If missile_propagation tracking list has not been set by any other thread, set missile_propagation
                self.layout[pos_x-1][pos_y-1] = request.soldier_id
                return missiledefence_pb2.NewCommanderFilter(soldier_id=request.soldier_id)
            else:
                self.status_requests_received[request.soldier_id]=0
        
        self.layout[pos_x-1][pos_y-1] = request.soldier_id
        return missiledefence_pb2.NewCommanderFilter(soldier_id=-1)

    # Form missile message using missile properties
    def form_message(self, sid, missile, updatedLayout):
        reply = missiledefence_pb2.MissileApproaching()
        reply.missile.CopyFrom(missiledefence_pb2.MissileDetails(
                position=missile["position"],
                time=missile["time"],
                type=missile["type"],
            ))
        reply.layout.extend(updatedLayout)
        return reply

    # Missile Server Streaming (once a client makes this request, stream is established.)
    def missile_approaching(self, request, context):
        # Wait till the first commander is elected
        while self.sid==-1:
            time.sleep(0.5)
            continue

        # Print initial layout (Only once)
        with lock:
            self.initial_layout_semaphore+=1
            if self.initial_layout_semaphore==1:
                logger.info("Initial layout: ")
                self.print_layout()

        for i in range(len(missile_launches)):
            # For each missile, take action for self and also inform soldiers.
            missile = missile_launches[i]
            missile_type = missile["type"]
            missile_time = missile["time"]
            missile_pos = missile["position"]

            # If a new commander is elected in between, he will skip the already sent messages
            if missile["sent"]:
                continue

            # The thread which executes FIRST will also take evasive action for SELF
            with lock:
                if self.take_shelter_semaphore == i:
                    if missile["position"][0] > self.war_zone_size or missile["position"][1] > self.war_zone_size:
                        # During the execution of the first thread, also check if the missile is within bounds.
                        # If drop location is outside war zone, the missile will be skipped for current and all subsequent threads.
                        missile["sent"] = True
                        logger.info(f"Skipping missile {missile_type} at time {missile_time} because {missile_pos} is outside the war zone..")
                        continue
                    self.take_shelter(missile_pos, missile_time, missile_type)
                    self.take_shelter_semaphore+=1

            # Update layout after taking action for self
            updatedLayout = []
            for layoutRow in self.layout:
                updatedLayout.append(missiledefence_pb2.LayoutRow(row=layoutRow))

            # If soldier dead, exit the thread of that particular soldier without giving a reply
            if request.soldier_id not in self.soldier_details.keys() or self.soldier_details[request.soldier_id]["is_alive"] == False:
                return
            
            reply = self.form_message(request.soldier_id, missile, updatedLayout)
            yield reply
            
            # Wait till every alive soldier updates the status before printing and proceeding to next missile
            while not all(v == i+1 for v in self.status_requests_received.values()):
                time.sleep(0.1)

            with lock:
                # Only print the updated layout once per missile in the thread which executes LAST
                if not self.is_war_over  and (self.updated_layout_semaphore == len(self.status_requests_received) or (self.no_of_soldiers - casuality_count) <= 1):
                    logger.info("Updated layout: ")
                    self.print_layout()
                    logger.info(f"Dead soldiers: {self.dead_soldiers}")
                    self.updated_layout_semaphore = 0

            missile_launches[i]["sent"] = True
            with lock:
                # Check war status and print only once if war is won or lost
                # Once war comes to some conclusion, only the first thread which executes this block of code will print the status.
                if not self.is_war_over:
                    if casuality_count >= 0.5 * self.no_of_soldiers:
                        logger.info("casuality_count >= 0.5*no_of_soldiers..")
                        logger.info("War lost!")
                        self.is_war_over = True
                    elif len(list(filter(lambda m: m["sent"]==False,missile_launches)))==0:
                        logger.info("War won!")
                        self.is_war_over = True
                    elif not self.is_alive and len(self.soldier_details) == 0:
                        logger.info("Commander dead, No one to elect.. War lost")
                        self.is_war_over = True
                        
                    if self.is_war_over:
                        logger.info("Final layout: ")
                        self.print_layout()
            
            if self.is_war_over:
                return

            # Sleep for 't' seconds before launching the next missile
            time.sleep(t)  # Change this to the desired 't' value

    # Upon election request, update the new commander details
    def elect_commander(self, request, context):
        logger.info(f"Electing {request.soldier_id} as the new commander ...")

        self.sid = request.soldier_id
        self.speed = request.speed
        self.position = request.position
        self.soldier_details[request.soldier_id]["position"] = request.position
        self.is_alive = True
        self.commander_dead_sent = False

        if request.soldier_id in self.status_requests_received.keys():
            # Remove tracking the particular soldier since he has now become the commander itself
            del self.status_requests_received[request.soldier_id]
            del self.soldier_details[request.soldier_id]

        return google.protobuf.empty_pb2.Empty()

    def updatePositions(self, soldier_id, position):
        old_pos_x = self.soldier_details[soldier_id]["position"][0]
        old_pos_y = self.soldier_details[soldier_id]["position"][1]
        new_pos_x = position[0]
        new_pos_y = position[1]
        if old_pos_x != new_pos_x or old_pos_y!=new_pos_y:
            self.soldier_details[soldier_id]["position"]=position
            self.layout[old_pos_x-1][old_pos_y-1] = 0
            self.layout[new_pos_x-1][new_pos_y-1] = soldier_id
            logger.info(f"Updating position of soldier {soldier_id} from {old_pos_x},{old_pos_y} to {new_pos_x},{new_pos_y}...")

    '''
    Update ALIVE status and position after movement upon request (if any)
    If the soldier which requested is alive, but the commander is dead by this time:
        If the commander has not asked any other soldier to be the new commander:
            Ask the current soldier to be the new commander
    '''
    def status(self, request, context):
        self.soldier_details[request.soldier_id]["is_alive"]=request.is_alive
            
        global casuality_count
        if request.is_alive == False:
            # If dead
            pos_x = self.soldier_details[request.soldier_id]["position"][0]
            pos_y = self.soldier_details[request.soldier_id]["position"][1]
            self.layout[pos_x-1][pos_y-1] = 0

            # Remove tracking details of the dead soldier
            self.dead_soldiers.append(request.soldier_id)
            del self.soldier_details[request.soldier_id]
            del self.status_requests_received[request.soldier_id]
            casuality_count+=1
        else:
            self.updatePositions(request.soldier_id, request.position)
        
        reply = missiledefence_pb2.CommanderStatus()
        election_needed = False
        if not self.is_alive and not self.commander_dead_sent:
            election_needed = True
            # If commander in currently in dead state and no soldier has been asked to become new commander
            del self.status_requests_received[request.soldier_id]
            self.commander_dead_sent = True
            pos_x = self.position[0]
            pos_y = self.position[1]
            self.layout[pos_x-1][pos_y-1] = 0

            soldiers = list(self.soldier_details)
            if len(soldiers) == 0:
                # If there are no more soldiers to elect commander
                reply.new_commander_id = -1
            else:
                reply.new_commander_id = random.choice(soldiers)
            casuality_count+=1
        else:
            reply.new_commander_id = -1

        if request.is_alive == True and not election_needed:
            # Update the number of status update requests received from the particular soldier for tracking purposes
            self.status_requests_received[request.soldier_id]+=1
            self.updated_layout_semaphore+=1

        return reply

    def print_layout(self):
        layout_string = "\n"
        for row in self.layout:
            for col in row:
                layout_string += str(col) + "     "
            layout_string += "\n"
        logger.info(layout_string)


    # commander as a soldier
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
            or self.position[0] > len(self.layout)
            or self.position[1] > len(self.layout[0])
            or self.layout[self.position[0]-1][self.position[1]-1] != 0
        ):
            self.position[0] = old_x
            self.position[1] = old_y
            return False
        self.layout[old_x-1][old_y-1] = 0
        self.layout[self.position[0]-1][self.position[1]-1] = self.sid
        return True

    def take_shelter(self, missile_position, time, missile_type):
        # Print current missile details
        logger.info("Time: {0}".format(time))
        logger.info("Missile type: {0}".format(missile_type))
        logger.info("Missile position: {0}".format(missile_position))
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
                        self.layout[self.position[0]-1][self.position[1]-1] = 0
                        self.is_alive = False
                        break
                else:
                    self.is_alive = False
                    break
            
            # If soldier dead, make soldier position 0 in layout
            if self.is_alive == False:
                self.dead_soldiers.append(self.sid)
                self.layout[self.position[0] - 1][self.position[1] - 1] = 0
                if self.sid in self.soldier_details.keys():
                    del self.soldier_details[self.sid]

        logger.info(f"has_moved: {has_moved}, New position of soldier {self.sid}: {self.position}...")


def take_missile_seq_input():
    global missile_launches
    no_of_missiles = int(T/t)
    logger.info(f"Please enter the type and position of your {no_of_missiles} missiles in the following format... Eg: M1:1,1  M2:1,2  M3:2,2  M4:3,2")
    while True:
        missile_launches = []
        missile_seq = list(input(f"Your missile sequence: ").split(" "))
        for i in range(len(missile_seq)):
            type_plus_pos = missile_seq[i].split(":")
            if len(type_plus_pos) != 2:
                break

            missile_type = type_plus_pos[0]
            if missile_type in missile_details.keys():
                position = type_plus_pos[1].split(",")
                if len(position) != 2:
                    break

                try:
                    missile_row = int(position[0])
                    missile_col = int(position[1])
                    if missile_row <= 0 or missile_col <= 0:
                        break
                    missile_launches.append({"position":[missile_row, missile_col], "time": t*i, "type": missile_type, "sent":False})
                except:
                    break
                
        if len(missile_launches) == no_of_missiles: 
            break
        else:
            logger.info("Please enter again with proper format.. Also check the missile position with war zone boundary values..")

def take_inputs():
    global T, t
    T = int(input("Please enter total time of war (T): "))
    while True:
        t = int(input("Please enter time per missile (t): "))
        if T%t == 0:
            break
        else:
            logger.info(f"Please enter any factor of the T which you have specified as {T}")
    take_missile_seq_input()

def start_commander():
    # Accept hyperparameters T, t and missile launch details
    take_inputs()
    port = commander_port

    # By default, gRPC "server" supports multi-threading out of the box
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    missiledefence_pb2_grpc.add_CommanderServicer_to_server(Commander(), server)
    server.add_insecure_port("[::]:" + port)

    # Server starts listening and will satisfy all requests which pertain to the Commander class
    server.start()
    logger.info("Server started, listening on " + port)
    server.wait_for_termination()


if __name__ == "__main__":
    start_commander()
