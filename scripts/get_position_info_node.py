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
        self.get_logger().info('位置查询服务已启动')


    def position_info_callback(self, request, response):
        """服务回调函数，处理位置查询请求"""


        self.get_logger().info(f'收到查询请求: "{query}"')
        response.position_info = "我在客厅"
        response.success = True
        self.get_logger().info("我在客厅")

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
