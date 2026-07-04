#!/usr/bin/env python3

import os
import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 平台兼容性设置
def configure_platform():
    """配置平台特定设置"""
    # 检测ARM架构
    is_arm = "aarch64" in os.uname().machine.lower()
    
    # 设置插件路径
    if is_arm:
        # 设置Qt插件路径（根据你的系统调整）
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/usr/lib/aarch64-linux-gnu/qt5/plugins"
        os.environ["QT_PLUGIN_PATH"] = "/usr/lib/aarch64-linux-gnu/qt5/plugins"
        logger.info("ARM架构插件路径已设置")
    
    # 高DPI设置
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1.0"
    
    # 其他优化设置
    os.environ["OPENCV_VIDEOIO_PRIORITY"] = "0"
    os.environ["QT_LOGGING_RULES"] = "qt.*.debug=false"
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    
    # 内存管理优化
    os.environ["MALLOC_CHECK_"] = "0"
    os.environ["MALLOC_PERTURB_"] = "0"
    os.environ["MALLOC_ARENA_MAX"] = "1"
    os.environ["MALLOC_MMAP_THRESHOLD_"] = "131072"
    
    # 增加虚拟内存限制
    try:
        import resource
        # 增加虚拟内存限制
        resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        # 增加堆栈大小
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        logger.info("资源限制设置成功")
    except Exception as e:
        logger.error(f"设置资源限制失败: {str(e)}")
    except ImportError:
        logger.warning("resource模块不可用，跳过资源限制设置")

# 配置平台
configure_platform()

# 现在导入其他模块
import cv2
import numpy as np
import tempfile

from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QLinearGradient, QBrush, QIcon
from route import MapWidget  # 导入修改后的地图组件

# 在导入PyQt5之后，创建QApplication之前添加
from PyQt5 import QtWidgets
QtWidgets.QApplication.addLibraryPath("/usr/lib/aarch64-linux-gnu/qt5/plugins")

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QHBoxLayout, QVBoxLayout, QFrame, QGraphicsDropShadowEffect,
    QSplitter, QSizePolicy
)

import os
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/usr/lib/aarch64-linux-gnu/qt5/plugins"

# ROS2 imports
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from custom_messages.msg import FaceMessage, VoiceMessage, EnvironmentMessage, RouteMessage
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from std_msgs.msg import Int8

# Import face and environment recognition functions
#import identify_face
#import environment_predict
import json_handle

class ROS2Thread(QThread):
    """ROS2 通信线程"""
    status_received = pyqtSignal(object)
    face_received = pyqtSignal(np.ndarray)  # face image
    voice_received = pyqtSignal(str)  # voice data
    environment_received = pyqtSignal(np.ndarray)  # environment image
    route_received = pyqtSignal(list, str)  # route_points, destination

    def __init__(self):
        super().__init__()
        self.running = True
        self.node = None  # 在子线程中初始化节点

    def run(self):
        logger.info("ROS2线程启动...")
        rclpy.init()
        # 在子线程中创建节点
        self.node = ROS2SubscriberNode()
        self.node.parent_thread = self
        logger.info("ROS2节点已创建")
        while self.running and rclpy.ok():
            rclpy.spin_once(self.node, timeout_sec=0.1)

        logger.info("清理ROS2节点...")
        self.node.destroy_node()
        rclpy.shutdown()
        logger.info("ROS2线程结束")

    def stop(self):
        self.running = False
        self.wait(2000)  # 等待线程结束


class ROS2SubscriberNode(Node):
    """ROS2 订阅节点"""

    def __init__(self):
        super().__init__('hmi_ros2_node')

        # 创建 CV bridge
        self.bridge = CvBridge()

        # 设置 QoS
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=10
        )

        # 创建订阅者
        self.status_sub = self.create_subscription(
            Int8,      #StatusMessage
            '/awake_flag',      #int8
            self.status_callback,
            qos
        )

        self.face_sub = self.create_subscription(
            Image,
            '/camera/color/image_raw',
            self.face_callback,
            qos
        )

        self.voice_sub = self.create_subscription(
            VoiceMessage,
            '/voice_message',
            self.voice_callback,
            qos
        )

        self.environment_sub = self.create_subscription(
            Image,
            '/image_raw',
            self.environment_callback,
            qos
        )

        self.route_sub = self.create_subscription(
            RouteMessage,
            '/route_message',
            self.route_callback,
            qos
        )

        self.get_logger().info('HMI ROS2 节点已启动')

    def status_callback(self, msg):
        """状态消息回调"""
        self.get_logger().info(f'收到状态消息: {msg} ')
        # 通过信号发送到主线程
        if hasattr(self, 'parent_thread'):
            self.parent_thread.status_received.emit(msg)

    def face_callback(self, msg):
        """人脸消息回调"""
        try:
            # 转换 ROS 图像消息为 OpenCV 图像
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            if hasattr(self, 'parent_thread'):
                self.parent_thread.face_received.emit(cv_image)
        except Exception as e:
            self.get_logger().error(f'处理人脸图像失败: {str(e)}')

    def voice_callback(self, msg):
        """语音消息回调"""
        self.get_logger().info(f'收到语音消息: {msg.voice_data}')
        if hasattr(self, 'parent_thread'):
            self.parent_thread.voice_received.emit(msg.voice_data)

    def environment_callback(self, msg):
        """环境消息回调"""
        try:
            # 转换 ROS 图像消息为 OpenCV 图像
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            if hasattr(self, 'parent_thread'):
                self.parent_thread.environment_received.emit(cv_image)
        except Exception as e:
            self.get_logger().error(f'处理环境图像失败: {str(e)}')

    def route_callback(self, msg):
        """路线消息回调"""
        self.get_logger().info(f'收到路线消息: {msg.destination}')
        if hasattr(self, 'parent_thread'):
            self.parent_thread.route_received.emit(msg.route_points, msg.destination)


class CardFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(36, 40, 56, 0.92);
                border-radius: 36px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 12)
        self.setGraphicsEffect(shadow)


class SceneVideoWidget(CardFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 360)
        self.setMaximumHeight(600)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(self.label)

        # 显示默认图像或占位符
        self.set_placeholder_image()

    def set_placeholder_image(self):
        """设置占位符图像"""
        # 创建一个简单的占位符图像
        placeholder = np.zeros((360, 600, 3), dtype=np.uint8)
        placeholder[:] = (50, 50, 50)  # 灰色背景
        self.update_image(placeholder)

    def update_image(self, cv_image):
        """更新显示的图像"""
        if cv_image is not None:
            # 调整图像大小
            cv_image = cv2.resize(cv_image, (600, 360))
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(qt_image))


class FaceVideoWidget(CardFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 360)
        self.setMaximumHeight(600)
        self.status = "未识别"
        self.detected = False
        self.last_frame = None
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(self.label)
        self.set_placeholder_image()

    def set_placeholder_image(self):
        """设置占位符图像"""
        placeholder = np.zeros((360, 600, 3), dtype=np.uint8)
        placeholder[:] = (50, 50, 50)
        self.update_image(placeholder)

    def update_image(self, cv_image):
        """更新显示的图像"""
        if cv_image is not None:
            self.last_frame = cv_image.copy()
            cv_image = cv2.resize(cv_image, (600, 360))
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # 创建新的绘图设备
            result_pixmap = QPixmap(pixmap.size())
            result_pixmap.fill(Qt.transparent)
            
            # 使用 QPainter 在新的 pixmap 上绘制
            painter = QPainter(result_pixmap)
            
            # 先绘制原始图像
            painter.drawPixmap(0, 0, pixmap)
            
            if self.detected:
                # 添加识别状态覆盖
                grad = QLinearGradient(0, 0, 600, 360)
                grad.setColorAt(0, QColor(72, 61, 139, 200))
                grad.setColorAt(1, QColor(0, 191, 255, 200))
                painter.fillRect(0, 0, 600, 360, QBrush(grad))
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setBrush(QColor(127, 0, 255, 230))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(250, 110, 100, 100)
                painter.setPen(Qt.white)
                font = QFont("Arial", 28, QFont.Bold)
                painter.setFont(font)
                painter.drawText(250, 110, 100, 100, Qt.AlignCenter, self.status)
            
            painter.end()
            self.label.setPixmap(result_pixmap)

    def set_detected(self, detected=True):
        """设置识别状态"""
        self.detected = detected
        self.status = "已识别" if detected else "未识别"
        if self.last_frame is not None:
            self.update_image(self.last_frame)


class CircleStatusButton(QPushButton):
    def __init__(self, icon_path_normal, icon_path_warning, color1, color2, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 90)
        self.color1 = color1
        self.color2 = color2
        self.icon_normal = QIcon(icon_path_normal)
        self.icon_warning = QIcon(icon_path_warning)
        self.update_style()
        
        # 设置初始图标
        self.setIcon(self.icon_normal)
        self.setIconSize(QSize(48, 48))

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)

    def update_style(self):
        """更新按钮样式"""
        self.setStyleSheet(f"""
            QPushButton {{
                border-radius: 45px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.color1}, stop:1 {self.color2});
                color: #fff;
                font-weight: bold;
                font-size: 40px;
                border: 2px solid rgba(255,255,255,0.10);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.color2}, stop:1 {self.color1});
            }}
        """)

    def set_status(self, is_normal):
        """设置状态（绿色表示正常，红色表示异常）"""
        if is_normal == 1:
            self.color1 = "#43e97b"
            self.color2 = "#38f9d7"
            self.setIcon(self.icon_normal)
        else:
            self.color1 = "#ff6b6b"
            self.color2 = "#ee5a24"
            self.setIcon(self.icon_warning)
        self.update_style()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('智慧导览系统 - ROS2版本')
        self.resize(1500, 900)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #23243a, stop:1 #2d3250);
            }
            QLabel, QTextEdit {
                color: #eaf6ff;
                font-size: 22px;
                font-family: 'Segoe UI', '微软雅黑', 'Arial';
            }
            QTextEdit {
                background: rgba(44,48,70,0.7);
                border-radius: 20px;
                padding: 12px;
            }
        """)

        # 状态标志
        self.camera_ok = False
        self.awake_flag = 0

        self._last_detected = False
        self._last_detected_ts = 0
        self._face_detect_timer = None
        self._face_detected_active = False

        # 初始化 ROS2 线程
        self.ros2_thread = ROS2Thread()
        
        # 连接信号
        self.ros2_thread.status_received.connect(self._on_awake_flag)
        self.ros2_thread.face_received.connect(self._on_camera_image)
        self.ros2_thread.voice_received.connect(self.process_voice_message)
        self.ros2_thread.environment_received.connect(self.process_environment_image)
        self.ros2_thread.route_received.connect(self.process_route_message)

        # 启动 ROS2 线程
        self.ros2_thread.start()

        self.init_ui()
        self.update_status_button()

    def _on_camera_image(self, cv_image):
        self.cam_btn.set_status(1)  # 绿色
        self.process_face_image(cv_image)

    def _on_awake_flag(self, msg):
        # msg可能是Uint8对象或int
        self.awake_flag = msg.data
        if self.awake_flag == 1:
            self.voice_btn.set_status(1)  # 绿色
        else:
            self.voice_btn.set_status(0)  # 红色
        self.update_status_button()

    def update_status_button(self):
        pass  # 按钮状态已在各自信号回调中单独处理

    def init_ui(self):
        # 左侧
        left_layout = QVBoxLayout()
        left_layout.setSpacing(36)
        scene_label = QLabel("场景理解")
        scene_label.setAlignment(Qt.AlignCenter)
        scene_label.setStyleSheet("font-size: 32px; font-weight: bold; letter-spacing: 2px; margin-bottom: 10px;")
        left_layout.addWidget(scene_label)
        self.scene_video = SceneVideoWidget()
        left_layout.addWidget(self.scene_video)
        face_label = QLabel("人脸识别")
        face_label.setAlignment(Qt.AlignCenter)
        face_label.setStyleSheet("font-size: 32px; font-weight: bold; letter-spacing: 2px; margin-bottom: 10px;")
        left_layout.addWidget(face_label)
        self.face_video = FaceVideoWidget()
        left_layout.addWidget(self.face_video)
        left_layout.addStretch(1)

        # 右侧
        right_layout = QVBoxLayout()
        right_layout.setSpacing(36)
        # 状态按钮均匀分布
        status_layout = QHBoxLayout()
        status_layout.addStretch(1)
        self.voice_btn = CircleStatusButton(
            "/home/sunrise/nav_car/car/src/hmi_ros2_node/icons/microphone.png", "/home/sunrise/nav_car/car/src/hmi_ros2_node/icons/microphone_warning.png", 
            "#ff6b6b", "#ee5a24"
        )
        self.cam_btn = CircleStatusButton(
            "/home/sunrise/nav_car/car/src/hmi_ros2_node/icons/camera.png", "/home/sunrise/nav_car/car/src/hmi_ros2_node/icons/camera_warning.png", 
            "#ff6b6b", "#ee5a24"
        )
        status_layout.addWidget(self.voice_btn)
        status_layout.addSpacing(60)
        status_layout.addWidget(self.cam_btn)
        status_layout.addStretch(1)
        right_layout.addLayout(status_layout)

        scene_card = CardFrame()
        scene_card_layout = QVBoxLayout(scene_card)
        scene_result_label = QLabel("场景理解检测结果")
        scene_result_label.setStyleSheet("font-size: 26px; font-weight: bold; margin-bottom: 6px;")
        scene_card_layout.addWidget(scene_result_label)
        self.scene_result = QTextEdit()
        self.scene_result.setFixedHeight(60)
        self.scene_result.setReadOnly(True)
        self.scene_result.setText("等待环境识别...")
        scene_card_layout.addWidget(self.scene_result)
        right_layout.addWidget(scene_card)

        face_card = CardFrame()
        face_card_layout = QVBoxLayout(face_card)
        face_result_label = QLabel("人脸检测结果")
        face_result_label.setStyleSheet("font-size: 26px; font-weight: bold; margin-bottom: 6px;")
        face_card_layout.addWidget(face_result_label)
        self.face_result = QTextEdit()
        self.face_result.setFixedHeight(60)
        self.face_result.setReadOnly(True)
        self.face_result.setText("等待人脸识别...")
        face_card_layout.addWidget(self.face_result)
        right_layout.addWidget(face_card)

        map_card = CardFrame()
        map_card.setFixedHeight(550)
        map_card_layout = QVBoxLayout(map_card)
        map_label = QLabel("平遥古城景点地图")
        map_label.setAlignment(Qt.AlignCenter)
        map_label.setStyleSheet("font-size: 26px; font-weight: bold; margin-bottom: 6px;")
        map_card_layout.addWidget(map_label)
        
        # 使用新的地图组件
        self.map_view = MapWidget()
        map_card_layout.addWidget(self.map_view)
        right_layout.addWidget(map_card, stretch=2)

        # QSplitter主布局
        self.splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([1, 1])
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: #444;
            }
        """)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(64, 48, 64, 48)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

    def update_status(self, is_normal):
        """更新状态按钮"""
        self.cam_btn.set_status(is_normal)
        logger.info(f"状态更新: {'正常' if is_normal else '异常'} ")

    def process_face_image(self, cv_image):
        """处理人脸图像"""
        # 更新人脸视频显示
        self.face_video.update_image(cv_image)
        self.face_video.set_detected(False)

        # 保存图像到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        cv2.imwrite(temp_file.name, cv_image)
        temp_file.close()

        try:
            # 调用人脸识别
            # result = identify_face.identify_face_from_image(temp_file.name)
            data = json_handle.read_json(False)
            result = data['success']
            detected = data.get('detected', False)
            ts = data.get('timestamp', 0)
            if result:
                result_text = data['result']
                # 只有新识别时才触发
                if detected and (ts != getattr(self, '_last_detected_ts', None)):
                    logger.info(f"新识别，定时器启动，timestamp={ts}")
                    self.face_video.set_detected(True)
                    if not hasattr(self, '_face_detect_timer') or self._face_detect_timer is None:
                        self._face_detect_timer = QTimer(self)
                        self._face_detect_timer.setSingleShot(True)
                        self._face_detect_timer.timeout.connect(self._on_face_detect_timeout)
                    self._face_detect_timer.stop()
                    self._face_detect_timer.start(5000)
                    self._face_detected_active = True
                    self._last_detected_ts = ts
            else:
                result_text = data['error_message']
            self.face_result.setText(result_text)

            #logger.info(f"人脸识别结果: {result_text}")
        except Exception as e:
            logger.error(f"人脸识别失败: {str(e)}")
            self.face_result.setText("识别失败")
        finally:
            # 删除临时文件
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"删除临时文件失败: {str(e)}")

    def _on_face_detect_timeout(self):
        self.face_video.set_detected(False)
        self._face_detected_active = False

    def process_voice_message(self, voice_data):
        """处理语音消息"""
        logger.info(f"收到语音消息: {voice_data}")
        # 可以在这里添加语音处理逻辑

    def process_environment_image(self, cv_image):
        """处理环境图像"""
        # 更新场景视频显示
        self.scene_video.update_image(cv_image)

        # 保存图像到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        cv2.imwrite(temp_file.name, cv_image)
        temp_file.close()

        try:
            # 调用环境识别
            # result = environment_predict.predict_environment_from_image(temp_file.name)
            data = json_handle.read_json(True)
            result = data['success']
            if result:
                result = data['result']
            else:
                result = data['error_message']
            self.scene_result.setText(result)
            #logger.info(f"环境识别结果: {result}")
        except Exception as e:
            logger.error(f"环境识别失败: {str(e)}")
            self.scene_result.setText("识别失败")
        finally:
            # 删除临时文件
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"删除临时文件失败: {str(e)}")

    def process_route_message(self, route_points, destination):
        """处理路线消息"""
        logger.info(f"收到路线消息: {destination}")
        try:
            # 更新地图显示
            if route_points:
                self.map_view.set_route_by_names(route_points)
        except Exception as e:
            logger.error(f"路线更新失败: {str(e)}")

    def resizeEvent(self, event):
        total = self.width() - 128  # 减去左右边距
        self.splitter.setSizes([total // 2, total // 2])
        super().resizeEvent(event)
        
    def closeEvent(self, event):
        # 清理资源
        logger.info("清理资源...")
        
        # 停止 ROS2 线程
        if hasattr(self, 'ros2_thread'):
            logger.info("停止ROS2线程...")
            self.ros2_thread.stop()
            if self.ros2_thread.isRunning():
                self.ros2_thread.wait(2000)  # 等待线程结束
        
        # 手动触发垃圾回收
        import gc
        logger.info("执行垃圾回收...")
        gc.collect()
        
        logger.info("关闭窗口...")
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())