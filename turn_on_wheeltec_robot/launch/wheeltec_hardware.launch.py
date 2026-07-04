import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import launch_ros.actions

#def launch(launch_descriptor, argv):
def generate_launch_description():
    bringup_dir = get_package_share_directory('turn_on_wheeltec_robot')
    launch_dir = os.path.join(bringup_dir, 'launch')
    wheeltec_robot = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'turn_on_wheeltec_robot.launch.py')),
    )
    wheeltec_lidar = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'wheeltec_lidar.launch.py')),
    )
    wheeltec_camera = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'wheeltec_camera.launch.py')),
    )
    wheeltec_mic = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'wheeltec_mic.launch.py')),
    )
    wheeltec_servo_platform= IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'wheeltec_servo_platform.launch.py')),
    )
    return LaunchDescription([
        wheeltec_robot,#底盘
        wheeltec_lidar,#激光
        wheeltec_camera,#摄像头
        wheeltec_mic,#麦克风阵列
        wheeltec_servo_platform,#二维云台
    ]

    )

