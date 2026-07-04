#!/usr/bin/env python3
import rclpy
from pyasn1_modules.rfc2985 import gender
from rclpy.node import Node
from deepface import DeepFace
from interfaces.srv import FaceIdentify
import os
import json
import tensorflow as tf
import numpy as np
from keras.utils import load_img, img_to_array
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import json_handle

class FaceIdentifyServiceNode(Node):
    """ROS2 人脸识别服务节点"""
    
    def __init__(self):
        super().__init__('face_identify_service_node')
        
        # 创建服务
        self.srv = self.create_service(
            FaceIdentify, 
            'face_identify', 
            self.face_identify_callback
        )


        # 订阅摄像头话题
        self.bridge = CvBridge()
        self.latest_image = None
        self.create_subscription(
            Image,
            '/camera/color/image_raw',  # 你实际的摄像头话题名
            self.camera_callback,
            10
        )

        self.get_logger().info('人脸识别服务已启动，等待请求...')

    def camera_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.latest_image = cv_image
        except Exception as e:
            self.get_logger().error(f'摄像头图像转换失败: {str(e)}')
    
    def preprocess_face(self, face_img):
        """预处理人脸图像"""
        face_img = cv2.resize(face_img, (96, 96))
        face_img = face_img / 255.0
        return np.expand_dims(face_img, axis=0)

    
    def face_identify_callback(self, request, response):
        """服务回调函数"""
        import time
        self.get_logger().info(f'收到识别请求')

        try:
            # 用最新摄像头帧
            if self.latest_image is None:
                response.success = False
                response.error_message = "没有收到摄像头图像"
                response.result = ""
                data = {
                    "result": response.result,
                    "success": response.success,
                    "error_message": response.error_message,
                    "detected": False,
                    "timestamp": int(time.time())
                }
                json_handle.save_to_json(data, False)
                return response



            # 进行预测
            #age_range, gender, gender_prob = self.predict_age_gender(self.latest_image)
            analysis = DeepFace.analyze(
                img_path=self.latest_image,
                actions=["age","gender"],
                enforce_detection=False
            )
            for face in enumerate(analysis):
                age_range = str(face[1]['age'])
                gender = str(face[1]['gender'])
                if face[1]['gender']['Man'] > face[1]['gender']['Woman']:
                    gender_str = "男"
                else:
                    gender_str = "女"


            # 返回格式化的字符串结果
            result = f"{gender_str}     {age_range}"

            response.success = True
            response.error_message = ""
            response.result = result

            self.get_logger().info(f'识别成功: {result}')

            data = {
                "result": response.result,
                "success": response.success,
                "error_message": response.error_message,
                "detected": True,
                "timestamp": int(time.time())
            }
            json_handle.save_to_json(data, False)

        except Exception as e:
            error_msg = f"识别失败: {str(e)}"
            self.get_logger().error(error_msg)
            response.success = False
            response.error_message = error_msg
            response.result = ""

            data = {
                "result": response.result,
                "success": response.success,
                "error_message": response.error_message,
                "detected": False,
                "timestamp": int(time.time())
            }
            json_handle.save_to_json(data, False)


        return response


def main(args=None):
    import json_handle
    data = {
        "result": "",
        "success": False,
        "error_message": "",
        "detected": False,
        "timestamp": 0
    }
    json_handle.save_to_json(data, False)
    rclpy.init(args=args)
    
    face_identify_service = FaceIdentifyServiceNode()
    
    try:
        rclpy.spin(face_identify_service)
    except KeyboardInterrupt:
        pass
    finally:
        face_identify_service.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main() 
