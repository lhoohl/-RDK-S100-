import json
'''
string result
bool success
string error_message 
'''
data = {
    "result": "",
    "success": False,
    "error_message": ""
}

env_file_path = "/home/sunrise/nav_car/car/src/environment_service/srv/env_message.json"
face_file_path = "/home/sunrise/nav_car/car/src/face_identify_service/srv/face_message.json"

#flag = true:env_file_path,  flag = false:face_file_path
def save_to_json(data, flag):
    file_path = ""
    if flag:
        file_path = env_file_path
    else:
        file_path = face_file_path
    #自动补全detected和timestamp字段
    if 'detected' not in data:
        data['detected'] = False
    if 'timestamp' not in data:
        import time
        data['timestamp'] = int(time.time())
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=4)
        print(f"数据已成功保存至{file_path}")
    except Exception as e:
        print(f"保存文件时出错：{str(e)}")

def read_json(flag):
    file_path = ""
    if flag:
        file_path = env_file_path
    else:
        file_path = face_file_path
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if 'detected' not in data:
            data['detected'] = False
        if 'timestamp' not in data:
            data['timestamp'] = int(time.time())
        return data

