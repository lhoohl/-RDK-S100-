from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='face_identify_service',
            executable='face_identify_service_node.py',
            name='face_identify_service_node',
            output='screen',
            parameters=[{
                # 可以在这里添加参数配置
            }]
        )
    ]) 