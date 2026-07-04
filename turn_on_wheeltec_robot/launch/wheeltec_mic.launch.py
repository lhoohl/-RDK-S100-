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
   mic_launch = IncludeLaunchDescription(        # 包含指定路径下的另外一个launch文件
      PythonLaunchDescriptionSource([os.path.join(
         get_package_share_directory('wheeltec_aiui'), 'launch'),
         '/aiui_start.launch.py'])
      )
   chat_launch = IncludeLaunchDescription(        # 包含指定路径下的另外一个launch文件
      PythonLaunchDescriptionSource([os.path.join(
         get_package_share_directory('ollama_ros_chat'), 'launch'),
         '/ollama_ros_chat.launch.py'])
      )   
   
   cir_photo_node = Node(
      package = 'circlephoto',
      executable = 'cir_photo',
      output='screen'
   )
   return LaunchDescription([                        # 返回launch文件的描述信息
      
      mic_launch,#启动麦克风阵列和语音合成功能
      chat_launch,#接入deepseek
      cir_photo_node,#转动舵机、摄像头识别人脸
   ])
