# turtlebot_delivery_Erum
 
A ROS 2 workspace with two packages implementing a TurtleBot3 delivery mission using a ROS 2 action:
 
- **`delivery_mission_interfaces`** — defines the `DeliveryMission` action (goal, result, and feedback fields).
- **`delivery_mission_controller`** — the `delivery_mission_node` action server, which drives the robot through pickup → pause → delivery phases, streams progress feedback, and handles cancellation and timeouts.
## 1. Step-by-step setup instructions
 
1. **Source ROS 2** (once per terminal session):
```bash
   source /opt/ros/jazzy/setup.bash
```
 
2. **Clone this repo into your workspace's `src/` folder**:
```bash
   mkdir -p ~/turtlebot_ws/src
   cd ~/turtlebot_ws/src
   git clone https://github.com/Erum330/turtlebot_delivery_Erum.git
```
 
3. **Build both packages** (the interfaces package builds first automatically, since the controller depends on it):
```bash
   cd ~/turtlebot_ws
   colcon build --packages-select delivery_mission_interfaces delivery_mission_controller
```
 
4. **Source the workspace**:
```bash
   source install/setup.bash
```
 
## 2. Every ROS 2 command used, and what it does
 
| Command | What it does |
|---|---|
| `colcon build --packages-select <pkg1> <pkg2>` | Builds the specified packages using ROS 2's standard build tool. |
| `source install/setup.bash` | Loads the built packages into the current terminal so `ros2 run`/`ros2 action send_goal` can find them. |
| `ros2 launch turtlebot3_gazebo <world>.launch.py` | Launches the TurtleBot3 Gazebo simulation. |
| `ros2 run delivery_mission_controller delivery_mission_node` | Starts the action server that carries out delivery missions. |
| `ros2 action list` | Lists active actions — confirms `delivery_mission` is being served. |
| `ros2 action info /delivery_mission` | Shows details about the action, including its type and any connected clients/servers. |
| `ros2 action send_goal /delivery_mission delivery_mission_interfaces/action/DeliveryMission "{speed: 0.2, pickup_duration: 3.0, delivery_duration: 4.0, timeout: 15.0}" --feedback` | Sends a mission goal from the terminal and streams live feedback as it runs. |
| `ros2 topic echo /cmd_vel` | Prints the raw velocity commands being published during the mission. |
 
## 3. How to test the node
 
1. **Terminal 1** — launch the Gazebo simulation:
```bash
   export TURTLEBOT3_MODEL=burger
   ros2 launch turtlebot3_gazebo <your_world>.launch.py
```
 
2. **Terminal 2** — run the action server:
```bash
   source ~/turtlebot_ws/install/setup.bash
   ros2 run delivery_mission_controller delivery_mission_node
```
 
3. **Terminal 3** — send a normal goal and watch it complete:
```bash
   source ~/turtlebot_ws/install/setup.bash
   ros2 action send_goal /delivery_mission delivery_mission_interfaces/action/DeliveryMission "{speed: 0.2, pickup_duration: 3.0, delivery_duration: 4.0, timeout: 15.0}" --feedback
```
   The robot should drive forward for 3s (pickup), stop for 1s (pause), then drive forward for 4s (delivery), then stop.
 
4. **Test cancellation**: send another goal, then press `Ctrl+C` in Terminal 3 partway through — the client library sends a cancel request, and the robot should stop immediately rather than finishing the phase.
5. **Test timeout**: send a goal with a `timeout` shorter than `pickup_duration + delivery_duration`, e.g.:
```bash
   ros2 action send_goal /delivery_mission delivery_mission_interfaces/action/DeliveryMission "{speed: 0.2, pickup_duration: 10.0, delivery_duration: 10.0, timeout: 5.0}" --feedback
```
   The mission should abort partway through with a timeout message instead of completing.
 
6. **Test goal rejection**: send an invalid goal (e.g. `speed: 0.0` or a negative duration) and confirm the goal is rejected before any movement happens.
## 4. Expected output
 
**Terminal 2 (action server) during a normal completed mission:**
```
[INFO] [delivery_mission_node]: Delivery Mission node started. Action server ready on "delivery_mission".
[INFO] [delivery_mission_node]: Accepting delivery mission goal: speed=0.2 m/s, pickup_duration=3.0s, delivery_duration=4.0s, timeout=15.0s.
[INFO] [delivery_mission_node]: Starting phase: pickup (3.0s)
[INFO] [delivery_mission_node]: Starting phase: pause (1.0s)
[INFO] [delivery_mission_node]: Starting phase: delivery (4.0s)
[INFO] [delivery_mission_node]: Delivery mission completed successfully in 8.0s.
```
 
**Terminal 3, streamed feedback (abbreviated):**
```
Feedback: delivery_mission_interfaces.action.DeliveryMission_FeedbackMessage(feedback=DeliveryMission_Feedback(current_phase='pickup', elapsed_time=0.4))
Feedback: delivery_mission_interfaces.action.DeliveryMission_FeedbackMessage(feedback=DeliveryMission_Feedback(current_phase='pause', elapsed_time=3.1))
Feedback: delivery_mission_interfaces.action.DeliveryMission_FeedbackMessage(feedback=DeliveryMission_Feedback(current_phase='delivery', elapsed_time=4.2))
Result:
delivery_mission_interfaces.action.DeliveryMission_Result(success=True, message='Delivery mission completed successfully in 8.0s.')
```
 
**Terminal 2, on a timeout:**
```
[WARN] [delivery_mission_node]: Mission timed out during phase "pickup" (elapsed 5.1s > timeout 5.0s).
```
 
**Terminal 2, on a cancel request:**
```
[INFO] [delivery_mission_node]: Cancel request received for delivery mission.
[INFO] [delivery_mission_node]: Phase "pickup" cancelled.
[INFO] [delivery_mission_node]: Delivery mission was cancelled by the client.
```
 
In Gazebo, the robot should visibly drive forward, pause, and drive forward again for a completed mission — and stop immediately on cancel or timeout rather than finishing its current motion.
 
## 5. Demo
Demo video:
 
## What did I learn from using AI?
 
I used Claude to scaffold the action server structure — the `goal_callback`/`cancel_callback`/`execute_callback` pattern rclpy expects, and the `MultiThreadedExecutor` setup needed so cancel requests can actually be processed while a goal is mid-execution (a single-threaded executor would block on the long-running `execute_callback` and never see the cancel come in). I reviewed and adjusted the phase-timing loop myself so that feedback streams continuously throughout each phase rather than only at the end, and made sure the robot always publishes a stop command on every exit path (success, cancel, or timeout) so it never keeps moving after the mission ends. This deepened my understanding of why ROS 2 actions exist as a third communication pattern alongside topics and services — they're specifically suited to long-running tasks that need progress feedback and support cancellation, which topics and services don't handle well on their own.
 
