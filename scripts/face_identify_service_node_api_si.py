#!/usr/bin/env python3
import rclpy
from pyasn1_modules.rfc2985 import gender
from rclpy.node import Node
from deepface import DeepFace
from face_identify_service.srv import FaceIdentify
import os
import json
import tensorflow as tf
import numpy as np
from keras.utils import load_img, img_to_array
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import json_handle

import requests
from openai import OpenAI
import base64

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

        self.Qwenclient = OpenAI(
              api_key="sk-58970a6ecd474bcbb8b4ca340ed96b24",
              base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
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

    def analyze_image(self, prompt = "返回照片中的人的大概年龄与性别，格式：男22"):
        try:
            # 直接将OpenCV图像数据传递给API
            # 首先将图像编码为JPEG格式的字节数据
            success, encoded_image = cv2.imencode('.jpg', self.latest_image)
            if not success:
                return "图像编码失败"

            # 将字节数据转换为base64编码
            base64_image = base64.b64encode(encoded_image.tobytes()).decode('utf-8')
            #构建请求消息
            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
            #发送请求到API
            completion = self.Qwenclient.chat.completions.create(
                model = "qwen-vl-plus",
                messages = messages
            )
            return completion.choices[0].message.content
        except Exception as e :
            return f"人脸图像处理处出错：{str(e)}"

    def extract_gender_and_age(self,input_str):
        #定义可能的性别标识
        gender_identifiers = ['男', '女']
        #查找性别标志的位置
        gender = None
        for identifier in gender_identifiers:
            if identifier in input_str:
                gender = identifier
                break
        if gender is None:
            return None,None
        #从字符串中移除性别部分，剩下的是年龄
        age_part = input_str.replace(gender,'')
        #提取数值部分作为年龄
        age = ''.join(filter(str.isdigit, age_part))
        age_length = len(age)
        if age_length > 2:
            age = age[-2 : ]
        return gender, age

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
            self.get_logger().info(f'开始向模型请求')
            #analysis = self.analyze_image()
            #self.get_logger().info(f'识别返回结果:{analysis}')

            #gender_str , age_range = self.extract_gender_and_age(analysis)
            gender_str = '男'
            age_range = '22'

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
