#!/usr/bin/env python3
"""
delivery_mission_node.py

This node is "the driver that carries out the delivery mission and
reports back on the progress."

What it does:
    - Hosts a DeliveryMission action server.
    - The goal specifies: speed, pickup_duration, delivery_duration,
      and timeout.
    - Drives the robot through 3 phases:
        Phase 1 (pickup):   drive forward for `pickup_duration` seconds
        Phase 2 (pause):    stop and simulate a pickup, while still
                             streaming feedback
        Phase 3 (delivery): drive forward for `delivery_duration`
                             seconds
    - Publishes velocity commands to /cmd_vel throughout.
    - Streams feedback (current_phase, elapsed_time) throughout the
      whole mission.
    - Aborts the mission if the total elapsed time exceeds `timeout`.
    - Stops the robot immediately if the client sends a cancel request.
    - Logs every phase and action to the ROS 2 console.
"""

import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

from geometry_msgs.msg import Twist

from delivery_mission_interfaces.action import DeliveryMission


CONTROL_PERIOD_SEC = 0.1


class DeliveryMissionNode(Node):
    """
    Action server that drives a TurtleBot3 through a pickup -> pause
    -> delivery mission, streaming feedback and supporting cancel and
    timeout handling.
    """

    def __init__(self):
        super().__init__('delivery_mission_node')

        self._callback_group = ReentrantCallbackGroup()

        self.cmd_vel_publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        self._action_server = ActionServer(
            self,
            DeliveryMission,
            'delivery_mission',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self._callback_group,
        )

        self.get_logger().info(
            'Delivery Mission node started. Action server ready on "delivery_mission".'
        )

    def goal_callback(self, goal_request):
        """Validate an incoming goal before accepting it."""
        if goal_request.speed <= 0:
            self.get_logger().warn('Rejecting goal: speed must be greater than 0.')
            return GoalResponse.REJECT

        if goal_request.pickup_duration < 0 or goal_request.delivery_duration < 0:
            self.get_logger().warn('Rejecting goal: durations cannot be negative.')
            return GoalResponse.REJECT

        if goal_request.timeout <= 0:
            self.get_logger().warn('Rejecting goal: timeout must be greater than 0.')
            return GoalResponse.REJECT

        self.get_logger().info(
            f'Accepting delivery mission goal: speed={goal_request.speed} m/s, '
            f'pickup_duration={goal_request.pickup_duration}s, '
            f'delivery_duration={goal_request.delivery_duration}s, '
            f'timeout={goal_request.timeout}s.'
        )
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        """Always accept cancel requests."""
        self.get_logger().info('Cancel request received for delivery mission.')
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        """Run the full 3-phase mission, streaming feedback, handling
        cancel and timeout, and returning a final result."""
        goal = goal_handle.request
        feedback_msg = DeliveryMission.Feedback()
        result = DeliveryMission.Result()

        mission_start_time = time.monotonic()

        def elapsed():
            return time.monotonic() - mission_start_time

        def timed_out():
            return elapsed() > goal.timeout

        def publish_feedback(phase_name):
            feedback_msg.current_phase = phase_name
            feedback_msg.elapsed_time = float(elapsed())
            goal_handle.publish_feedback(feedback_msg)

        def stop_robot():
            self.cmd_vel_publisher.publish(Twist())

        def run_timed_phase(phase_name, duration, linear_x):
            self.get_logger().info(f'Starting phase: {phase_name} ({duration}s)')
            phase_start = time.monotonic()

            while (time.monotonic() - phase_start) < duration:
                if goal_handle.is_cancel_requested:
                    stop_robot()
                    self.get_logger().info(f'Phase "{phase_name}" cancelled.')
                    return 'cancelled'

                if timed_out():
                    stop_robot()
                    self.get_logger().warn(
                        f'Mission timed out during phase "{phase_name}" '
                        f'(elapsed {elapsed():.1f}s > timeout {goal.timeout}s).'
                    )
                    return 'timed_out'

                twist = Twist()
                twist.linear.x = linear_x
                self.cmd_vel_publisher.publish(twist)

                publish_feedback(phase_name)
                time.sleep(CONTROL_PERIOD_SEC)

            return 'completed'

        outcome = run_timed_phase('pickup', goal.pickup_duration, goal.speed)

        if outcome == 'completed':
            outcome = run_timed_phase('pause', 1.0, 0.0)

        if outcome == 'completed':
            outcome = run_timed_phase('delivery', goal.delivery_duration, goal.speed)

        stop_robot()

        if outcome == 'cancelled':
            goal_handle.canceled()
            result.success = False
            result.message = 'Delivery mission was cancelled by the client.'
            self.get_logger().info(result.message)
            return result

        if outcome == 'timed_out':
            goal_handle.abort()
            result.success = False
            result.message = (
                f'Delivery mission aborted: exceeded timeout of {goal.timeout}s '
                f'(elapsed {elapsed():.1f}s).'
            )
            self.get_logger().warn(result.message)
            return result

        goal_handle.succeed()
        result.success = True
        result.message = (
            f'Delivery mission completed successfully in {elapsed():.1f}s.'
        )
        self.get_logger().info(result.message)
        return result


def main(args=None):
    """Initialize rclpy, spin the node with a multi-threaded executor
    (needed so cancel requests can be processed while a goal is
    executing), and clean up on exit."""
    rclpy.init(args=args)

    node = DeliveryMissionNode()
    executor = MultiThreadedExecutor()

    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        node.get_logger().info('Delivery Mission node shutting down.')
    finally:
        node.cmd_vel_publisher.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
