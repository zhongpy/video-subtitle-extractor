import os
import requests
import json
from tqdm import tqdm

# 配置
SOURCE_FOLDER = r'D:\BaiduNetdiskDownload'  # 输入源文件夹（绝对路径）
TARGET_FOLDER = r'D:\Temp'  # 目标文件夹（绝对路径）

# 当前运行目录中的记录文件
CURRENT_DIR = os.getcwd()
PROCESSED_RECORD = os.path.join(CURRENT_DIR, 'processed.json')  # 已处理记录文件
FAILED_LOG = os.path.join(CURRENT_DIR, 'failed.log')  # 处理失败日志文件

API_URL = 'http://127.0.0.1:5000/process'  # 后端 API 地址

# 支持的扩展名（常见视频格式）
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'}

# 初始化已处理记录文件
def load_processed_record():
    """
    加载已处理的文件记录。
    """
    if os.path.exists(PROCESSED_RECORD):
        with open(PROCESSED_RECORD, 'r') as f:
            return set(json.load(f))
    else:
        return set()

def save_processed_record(processed_files):
    """
    保存已处理的文件记录。
    """
    with open(PROCESSED_RECORD, 'w') as f:
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
            video_list.append((unique_id, file_path, target_path))
    return video_list

# 遍历源文件夹并调用 API
def process_videos():
    """
    遍历文件夹处理视频文件，显示进度条并记录失败日志。
    """
    processed_files = load_processed_record()
    video_list = get_video_list()
    total_videos = len(video_list)

    if not os.path.exists(SOURCE_FOLDER):
        print(f"Source folder '{SOURCE_FOLDER}' does not exist.")
        return

    # 使用 tqdm 显示进度条
    with tqdm(total=total_videos, desc='Processing videos') as pbar:
        for unique_id, file_path, target_file_path in video_list:
            if unique_id in processed_files:
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

                    processed_files.add(unique_id)
                    save_processed_record(processed_files)
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

    print("All files processed.")

if __name__ == '__main__':
    # 确保目标文件夹存在
    os.makedirs(TARGET_FOLDER, exist_ok=True)
    print(f"Processing videos in '{SOURCE_FOLDER}'...")
    process_videos()
