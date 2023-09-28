# missile-defense-system

Group  Members:
1. TV Abhinav Viswanaath  (2023H1120182P)
2. Dhruv Khurana  (2023H1120185P)
  
Instructions to run the program:

1. Ensure that Python and pip are installed on your system.
2. Install gRPC and clone our GitHub repository. 
3. Change the port numbers in commander.py if trying to run on 2 different machines. Change commander url as per your system IP address and the above configured port number inside soldier.py.  
4. First run commander.py.
5. Input hyperparameters related to missile launch in commander.py which are T (War time), t (Duration after each missile hits) and Missile Sequence (Missiles with their target positions).
6. Run soldier.py.
7. Input the hyperparameters in soldier.py - N (NxN is the size of warzone), M (No. of soldiers<=NxN), Soldier positions and their corresponding speeds (Si). Our warzone has the row and column index starting from 1, please ensure not to put zero while entering soldier positions. 
8. War starts. Program output can be checked from the logs. (Zero in the print layout means the position is empty while a number indicates the soldier_id of a soldier standing in that position.)



Note: If you are trying to run commander.py and soldier.py on different machines, you might be required first to unblock the firewalls of target or source systems to allow incoming/outgoing traffic.     
