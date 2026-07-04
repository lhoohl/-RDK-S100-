#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
位置查询服务节点
提供当前位置和导航目的点查询功能
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from interfaces.srv import GetPositionInfo
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
import yaml
import os
from ament_index_python.packages import get_package_share_directory


class PositionInfoService(Node):
    def __init__(self):
        super().__init__('position_info_service')

        # 创建服务
        self.srv = self.create_service(
            GetPositionInfo,
            'get_position_info',
            self.position_info_callback
        )

        # TF监听器，用于获取机器人当前位姿
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # 加载航点配置
        self.waypoints = {}
        self.load_waypoints()

        # 当前目标航点（可选，如果需要跟踪当前导航目标）
        self.current_goal = None

        self.get_logger().info('位置查询服务已启动')

    def load_waypoints(self):
        """加载航点配置文件"""
        try:
            # 尝试从largemodel包加载配置
            pkg_share = get_package_share_directory('largemodel')
            config_path = os.path.join(pkg_share, 'config', 'map_mapping.yaml')

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    waypoints_data = yaml.safe_load(f)

                if waypoints_data:
                    for key, value in waypoints_data.items():
                        name = value.get('name', key)
                        position = value.get('position', {})
                        orientation = value.get('orientation', {})

                        pose = PoseStamped()
                        pose.header.frame_id = 'map'
                        pose.pose.position.x = position.get('x', 0.0)
                        pose.pose.position.y = position.get('y', 0.0)
                        pose.pose.position.z = position.get('z', 0.0)
                        pose.pose.orientation.x = orientation.get('x', 0.0)
                        pose.pose.orientation.y = orientation.get('y', 0.0)
                        pose.pose.orientation.z = orientation.get('z', 0.0)
                        pose.pose.orientation.w = orientation.get('w', 1.0)

                        self.waypoints[name] = {
                            'key': key,
                            'pose': pose
                        }

                    self.get_logger().info(f'成功加载 {len(self.waypoints)} 个航点')
            else:
                self.get_logger().warn(f'配置文件不存在: {config_path}')

        except Exception as e:
            self.get_logger().error(f'加载航点配置失败: {e}')

    def get_current_pose(self):
        """获取机器人当前位姿"""
        try:
            transform = self.tf_buffer.lookup_transform(
                'map',
                'base_footprint',
                rclpy.time.Time()
            )

            current_pose = PoseStamped()
            current_pose.header.frame_id = 'map'
            current_pose.pose.position.x = transform.transform.translation.x
            current_pose.pose.position.y = transform.transform.translation.y
            current_pose.pose.position.z = transform.transform.translation.z
            current_pose.pose.orientation.x = transform.transform.rotation.x
            current_pose.pose.orientation.y = transform.transform.rotation.y
            current_pose.pose.orientation.z = transform.transform.rotation.z
            current_pose.pose.orientation.w = transform.transform.rotation.w

            return current_pose, True

        except Exception as e:
            self.get_logger().warn(f'获取当前位姿失败: {e}')
            return None, False

    def format_pose_info(self, pose, name=""):
        """格式化位姿信息为可读字符串"""
        if pose is None:
            return "未知位置"

        x = pose.pose.position.x
        y = pose.pose.position.y

        if name:
            return f"{name} (坐标: x={x:.2f}, y={y:.2f})"
        else:
            return f"坐标: x={x:.2f}, y={y:.2f}"

    def position_info_callback(self, request, response):
        """服务回调函数，处理位置查询请求"""
        query = request.query.strip()

        self.get_logger().info(f'收到查询请求: "{query}"')

        # 查询"你要去哪里" - 返回导航目的点（航点4/工具间）
        if '你要去哪里' in query or '去哪里' in query or '目的地' in query:
            # 查找航点4（根据你的需求，这里假设是索引为4的航点）
            # 你可以根据实际情况修改这个逻辑

            # 方式1: 按名称查找（推荐）
            target_waypoint_name = '工具间'  # 航点4的名称

            if target_waypoint_name in self.waypoints:
                waypoint_info = self.waypoints[target_waypoint_name]
                pose = waypoint_info['pose']
                key = waypoint_info['key']

                response.position_info = f"我要去{target_waypoint_name}（航点{key}）\n{self.format_pose_info(pose, target_waypoint_name)}"
                response.success = True
                self.get_logger().info(f'返回目的点: {target_waypoint_name}')
            else:
                # 如果找不到指定的航点，列出所有可用航点
                available_waypoints = list(self.waypoints.keys())
                response.position_info = f"未找到航点4，可用航点: {', '.join(available_waypoints)}"
                response.success = False
                response.error_message = "指定的航点不存在"

        # 查询"你在哪" - 返回出发点（航点3/便利店）或当前位置
        elif '你在哪' in query or '在哪里' in query or '当前位置' in query:
            # 获取当前实际位置
            current_pose, success = self.get_current_pose()

            if success and current_pose:
                # 方式1: 返回当前实际位置
                response.position_info = f"我当前位置在\n{self.format_pose_info(current_pose)}"
                response.success = True

                # 方式2: 如果要返回特定的出发点（航点3）
                # start_waypoint_name = '便利店'  # 航点3的名称
                # if start_waypoint_name in self.waypoints:
                #     waypoint_info = self.waypoints[start_waypoint_name]
                #     pose = waypoint_info['pose']
                #     key = waypoint_info['key']
                #     response.position_info = f"我在{start_waypoint_name}（航点{key}）\n{self.format_pose_info(pose, start_waypoint_name)}"
                #     response.success = True
                # else:
                #     response.position_info = f"我当前位置在\n{self.format_pose_info(current_pose)}"
                #     response.success = True

                self.get_logger().info('返回当前位置')
            else:
                # 如果无法获取当前位置，返回出发点信息
                start_waypoint_name = '便利店'  # 航点3的名称
                if start_waypoint_name in self.waypoints:
                    waypoint_info = self.waypoints[start_waypoint_name]
                    pose = waypoint_info['pose']
                    key = waypoint_info['key']
                    response.position_info = f"我在{start_waypoint_name}（航点{key}）\n{self.format_pose_info(pose, start_waypoint_name)}"
                    response.success = True
                else:
                    response.position_info = "无法获取位置信息"
                    response.success = False
                    response.error_message = "无法获取当前位置和出发点信息"

        # 查询所有航点
        elif '所有航点' in query or '航点列表' in query:
            if self.waypoints:
                info_lines = ["可用航点列表:"]
                for name, info in self.waypoints.items():
                    pose = info['pose']
                    key = info['key']
                    info_lines.append(
                        f"- {name} (航点{key}): x={pose.pose.position.x:.2f}, y={pose.pose.position.y:.2f}")

                response.position_info = "\n".join(info_lines)
                response.success = True
            else:
                response.position_info = "没有可用的航点信息"
                response.success = False
                response.error_message = "航点列表为空"

        # 查询特定航点
        elif any(name in query for name in self.waypoints.keys()):
            # 查找匹配的航点名称
            matched_name = None
            for name in self.waypoints.keys():
                if name in query:
                    matched_name = name
                    break

            if matched_name:
                waypoint_info = self.waypoints[matched_name]
                pose = waypoint_info['pose']
                key = waypoint_info['key']
                response.position_info = f"{matched_name}（航点{key}）\n{self.format_pose_info(pose, matched_name)}"
                response.success = True
            else:
                response.position_info = f"未找到航点: {query}"
                response.success = False
                response.error_message = "航点不存在"

        # 未知查询
        else:
            response.position_info = f"无法识别的查询: {query}\n支持的查询:\n- '你在哪' / '在哪里' / '当前位置'\n- '你要去哪里' / '去哪里' / '目的地'\n- '所有航点' / '航点列表'\n- 具体航点名称"
            response.success = False
            response.error_message = "不支持的查询类型"

        return response


def main(args=None):
    rclpy.init(args=args)
    node = PositionInfoService()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('服务节点被中断')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
