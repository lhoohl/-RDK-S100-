from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='hmi_ros2_node',
            executable='main.py',
            name='hmi_ros2_node',
            output='screen',
            parameters=[{
                # 可以在这里添加参数配置
            }]
        )
    ]) 