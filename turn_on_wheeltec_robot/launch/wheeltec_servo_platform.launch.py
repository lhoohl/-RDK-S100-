import os
from ament_index_python.packages import get_package_share_directory  # 查询功能包路径的方法
from launch_ros.actions import Node
from launch import LaunchDescription                 # launch文件的描述类
from launch.actions import IncludeLaunchDescription  # 节点启动的描述类
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.actions import GroupAction               # launch文件中的执行动作
from launch_ros.actions import PushRosNamespace      # ROS命名空间配置AnyLaunchDescriptionSource

def generate_launch_description():                   # 自动生成launch文件的函数

   servo_platform_node = Node(
      package = 'servo_platform_controller',
      executable = 'servo_controller',
      output='screen'
   )
   return LaunchDescription([                        # 返回launch文件的描述信息
      

      servo_platform_node,#二维云台
   ])
