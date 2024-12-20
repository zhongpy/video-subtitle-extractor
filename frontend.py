import os
import requests
import json
from tqdm import tqdm
from threading import Thread
import time  # 示例前端处理用
import shutil  # 用于复制文件

# 配置
SOURCE_FOLDER = r'D:\BaiduNetdiskDownload'  # 输入源文件夹（绝对路径）
TARGET_FOLDER = r'D:\Temp'  # 后端处理的目标文件夹（绝对路径）

# 当前运行目录中的记录文件
CURRENT_DIR = os.getcwd()
PROCESSED_RECORD = os.path.join(CURRENT_DIR, 'processed.json')  # 后端已处理记录文件
FAILED_LOG = os.path.join(CURRENT_DIR, 'failed.log')  # 后端处理失败日志文件

# 前端处理相关配置
FRONTEND_PROCESSED_FOLDER = os.path.join(CURRENT_DIR, 'FrontendProcessed')  # 前端处理结果文件夹
FRONTEND_PROCESSED_RECORD = os.path.join(CURRENT_DIR, 'frontend_processed.json')  # 前端已处理记录文件

API_URL = 'http://127.0.0.1:5000/process'  # 后端 API 地址

# 支持的扩展名（常见视频格式）
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'}

# 初始化已处理记录文件
def load_processed_record(record_file):
    """
    加载处理记录文件。
    """
    if os.path.exists(record_file):
        with open(record_file, 'r') as f:
            return set(json.load(f))
    else:
        return set()

def save_processed_record(record_file, processed_files):
    """
    保存处理记录文件。
    """
    with open(record_file, 'w') as f:
        json.dump(list(processed_files), f)

# 初始化失败日志文件
def log_failed_video(video_id, error_message):
    """
    记录处理失败的视频到日志文件。
    """
    with open(FAILED_LOG, 'a') as f:
        f.write(f"{video_id}: {error_message}\n")

# 获取待处理的视频列表
def get_video_list():
    """
    获取所有待处理的视频文件列表，仅保留支持的视频格式。
    """
    video_list = []
    for root, _, files in os.walk(SOURCE_FOLDER):
        relative_path = os.path.relpath(root, SOURCE_FOLDER)
        series_name = os.path.basename(root)
        if not files:
            continue
        for file_name in files:
            # 检查扩展名是否为视频
            if os.path.splitext(file_name)[1].lower() not in VIDEO_EXTENSIONS:
                continue
            unique_id = os.path.join(series_name, file_name)
            file_path = os.path.join(root, file_name)
            target_path = os.path.join(TARGET_FOLDER, relative_path, file_name)
            frontend_processed_path = os.path.join(FRONTEND_PROCESSED_FOLDER, relative_path, file_name)
            video_list.append((unique_id, file_path, target_path, frontend_processed_path))
    return video_list

# 模拟前端处理模块
def frontend_process(video_list, frontend_processed_files):
    """
    独立线程：处理前端视频文件。
    """
    print("[Frontend] Starting frontend processing...")
    for unique_id, file_path, _, frontend_processed_path in video_list:
        if unique_id in frontend_processed_files:
            print(f"[Frontend] Skipping {unique_id}, already processed.")
            continue
        try:
            # 确保目标文件夹存在
            os.makedirs(os.path.dirname(frontend_processed_path), exist_ok=True)

            # 模拟前端处理逻辑
            print(f"[Frontend] Processing {file_path}...")
            time.sleep(2)  # 模拟耗时
            shutil.copy(file_path, frontend_processed_path)  # 示例操作：复制文件

            # 标记为已处理
            frontend_processed_files.add(unique_id)
            save_processed_record(FRONTEND_PROCESSED_RECORD, frontend_processed_files)
            print(f"[Frontend] Saved processed video to {frontend_processed_path}")
        except Exception as e:
            print(f"[Frontend] Error processing {unique_id}: {str(e)}")
    print("[Frontend] Frontend processing complete.")

# 处理后端发送逻辑
def backend_process(video_list, backend_processed_files):
    """
    独立线程：发送视频文件到后端。
    """
    print("[Backend] Starting backend processing...")
    total_videos = len(video_list)

    with tqdm(total=total_videos, desc='Backend Processing') as pbar:
        for unique_id, file_path, target_file_path, _ in video_list:
            if unique_id in backend_processed_files:
                pbar.update(1)
                pbar.set_postfix({'Status': f"Skipped {unique_id}"})
                continue
            try:
                # 确保目标文件夹存在
                os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

                # 调用后端 API
                with open(file_path, 'rb') as f:
                    response = requests.post(API_URL, files={'file': f})

                if response.status_code == 200:
                    # 保存处理后的视频到目标文件夹
                    with open(target_file_path, 'wb') as f_out:
                        f_out.write(response.content)

                    backend_processed_files.add(unique_id)
                    save_processed_record(PROCESSED_RECORD, backend_processed_files)
                    pbar.set_postfix({'Status': f"Processed {unique_id}"})
                else:
                    error_message = response.json().get('error', 'Unknown error')
                    log_failed_video(unique_id, error_message)
                    pbar.set_postfix({'Status': f"Failed {unique_id}"})
            except Exception as e:
                # 记录异常并继续处理下一个视频
                log_failed_video(unique_id, str(e))
                pbar.set_postfix({'Status': f"Error {unique_id}"})

            pbar.update(1)

    print("[Backend] Backend processing complete.")

if __name__ == '__main__':
    # 确保目标文件夹存在
    os.makedirs(TARGET_FOLDER, exist_ok=True)
    os.makedirs(FRONTEND_PROCESSED_FOLDER, exist_ok=True)

    # 加载处理记录
    backend_processed_files = load_processed_record(PROCESSED_RECORD)
    frontend_processed_files = load_processed_record(FRONTEND_PROCESSED_RECORD)

    # 获取待处理文件列表
    video_list = get_video_list()

    # 启动前端和后端的独立线程
    frontend_thread = Thread(target=frontend_process, args=(video_list, frontend_processed_files))
    backend_thread = Thread(target=backend_process, args=(video_list, backend_processed_files))

    frontend_thread.start()
    backend_thread.start()

    frontend_thread.join()
    backend_thread.join()

    print("All processing complete.")
