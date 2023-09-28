# missile-defense-system

Group  Members:
1. TV Abhinav Viswanaath  (2023H1120182P)
2. Dhruv Khurana  (2023H1120185P)

   
Instructions to run the program:

1. Ensure that Python and pip (usually comes with Python) are installed on your system.
2. Install gRPC on your system using following commands:
   python -m pip install grpcio
   python -m pip install grpcio-tools
3. Clone our GitHub repository on your systems.
4. Change the port numbers in commander.py if trying to run on 2 different machines. Change commander url as per your system IP address and the above configured port number inside soldier.py.  
5. First run commander.py.
6. Input hyperparameters related to missile launch in commander.py which are T (War time), t (Duration after each missile hits) and Missile Sequence (Missiles with their target positions).
7. Run soldier.py.
8. Input the hyperparameters in soldier.py - N (NxN is the size of warzone), M (No. of soldiers<=NxN), Soldier positions and their corresponding speeds (Si). Our warzone has the row and column index starting from 1, please ensure not to put zero while entering soldier positions. 
9. War starts. Program output can be checked from the console as well as logs. A separate folder named logs can be found in our code which has all the output logs generated while running the code.
 (Zero in the print layout means position is empty while a number indicates the soldier_id of a soldier standing in that position.)

Note: 
i) If you are trying to run commander.py and soldier.py on different machines, you might be required to first unblock the firewalls of target or source systems to allow incoming/outgoing traffic.
ii) For understandability, we have performed the video recording demo on one machine (localhost), but we have successfully run the files (commander.py and soldier.py) on 2 separate machines while testing.

