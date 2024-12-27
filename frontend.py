import os
import requests
import json
from tqdm import tqdm
from threading import Thread, Event, Lock
import time  # 示例前端处理用
import shutil  # 用于复制文件
from pathlib import Path
from backend.main import SubtitleExtractor  # 导入字幕提取模块的核心类
import configparser
import cv2

# 配置
SOURCE_FOLDER = r'D:\BaiduNetdiskDownload\55部'  # 输入源文件夹（绝对路径）
TARGET_FOLDER = r'E:\Temp'  # 后端处理的目标文件夹（绝对路径）

# 当前运行目录中的记录文件
CURRENT_DIR = os.getcwd()
PROCESSED_RECORD = os.path.join(CURRENT_DIR, 'processed.json')  # 后端已处理记录文件
FAILED_LOG = os.path.join(CURRENT_DIR, 'failed.log')  # 后端处理失败日志文件
FRONTEND_PROCESSED_FOLDER = os.path.join(CURRENT_DIR, 'FrontendProcessed')  # 前端处理结果文件夹
FRONTEND_PROCESSED_RECORD = os.path.join(CURRENT_DIR, 'frontend_processed.json')  # 前端已处理记录文件
SUBTITLE_RECORD = os.path.join(CURRENT_DIR, 'subtitle_processed.json')  # 字幕提取记录文件

SUBTITLE_CONFIG=os.path.join(CURRENT_DIR, 'subtitle.ini') #字幕区域配置

API_URL = 'http://127.0.0.1:5000/process'  # 后端 API 地址
BACKEND_SERVERS = [
    'http://127.0.0.1:5000/process',
    'http://192.168.31.2:5000/process'
]

# 支持的扩展名（常见视频格式）
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'}

# 停止事件，用于安全关闭线程
STOP_EVENT = Event()

# 线程锁
PROCESS_LOCK = Lock()
FAILED_LOCK = Lock()

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

# 记录失败日志
def log_failed_video(video_id, error_message):
    with FAILED_LOCK:  # 确保线程安全
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
        if STOP_EVENT.is_set():  # 检查是否收到停止信号
            print("[Frontend] frontend_process extraction interrupted.")
            break
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

global_SubExtractor = None
# 字幕提取逻辑
def extract_subtitles(video_list, subtitle_processed_files):
    """
    对视频列表进行字幕提取。
    """
    print("[Frontend] Starting subtitle extraction...")
    # 假设输入比例值
    y_p = 0.6  # ymin 相对于 frame_height 的比例
    h_p = 0.35  # (ymax - ymin) 相对于 frame_height 的比例
    x_p = 0.0  # xmin 相对于 frame_width 的比例
    w_p = 1.0  # (xmax - xmin) 相对于 frame_width 的比例
    subtitle_area=(0.6, 0.35, 0.0, 1.0)
    for unique_id, file_path, _, _ in tqdm(video_list, desc="Subtitle Extraction"):
        if STOP_EVENT.is_set():  # 检查是否收到停止信号
            print("[Frontend] Subtitle extraction interrupted.")
            break
        if unique_id in subtitle_processed_files:
            print(f"[Frontend] Skipping {unique_id}, already processed.")
            continue
        video_cap = cv2.VideoCapture(file_path)
        if video_cap is None:
            continue
        if video_cap.isOpened():
            ret, frame = video_cap.read()
            frame_height = video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    # 获取视频的宽度
            frame_width = video_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            # 将比例转换为像素
            ymin = int(y_p * frame_height)
            ymax = int((y_p + h_p) * frame_height)
            xmin = int(x_p * frame_width)
            xmax = int((x_p + w_p) * frame_width)

            # 确保 ymax 和 xmax 不超过帧的边界
            if ymax > frame_height:
                ymax = frame_height
            if xmax > frame_width:
                xmax = frame_width
            subtitle_area=(ymin,ymax,xmin,xmax)
            video_cap.release()
        try:
            # 提取字幕
            video_name = Path(file_path).stem
            series_name = Path(file_path).parent.name
            output_path = os.path.join(TARGET_FOLDER, "Subtitle", series_name, "zh_hans")
            os.makedirs(output_path, exist_ok=True)

            # 使用 SubtitleExtractor 进行提取
            global_SubExtractor = SubtitleExtractor(file_path,subtitle_area)
            global_SubExtractor.run()
            global_SubExtractor.completed_event.wait()
            # 移动字幕文件到目标目录
            raw_srt_file = os.path.join(os.path.splitext(file_path)[0] + ".srt")
            if os.path.exists(raw_srt_file):
                target_srt_path = os.path.join(output_path, f"{video_name}.srt")
                shutil.move(raw_srt_file, target_srt_path)
                print(f"[Frontend] Subtitle saved to: {target_srt_path}")
                subtitle_processed_files.add(unique_id)
                save_processed_record(SUBTITLE_RECORD, subtitle_processed_files)
            else:
                print(f"[Frontend] No subtitle generated for: {file_path}")
        except Exception as e:
            print(f"[Frontend] Error extracting subtitles for {file_path}: {str(e)}")
    print("[Frontend] Subtitle extraction complete.")
# 添加一个全局的“正在处理”缓存标志
IN_PROGRESS_CACHE = set()
# 后端处理逻辑
def backend_process(video_list, backend_processed_files, api_url):
    """
    处理指定后端服务器的任务，支持缓存以避免重复处理。
    """
    print(f"[Backend] Starting processing with {api_url}...")
    total_videos = len(video_list)

    with tqdm(total=total_videos, desc=f'Processing with {api_url}') as pbar:
        for unique_id, file_path, target_file_path, _ in video_list:
            if STOP_EVENT.is_set():
                print(f"[Backend] Processing with {api_url} interrupted.")
                break

            # 检查是否已处理或正在处理
            with PROCESS_LOCK:
                if unique_id in backend_processed_files or unique_id in IN_PROGRESS_CACHE:
                    pbar.update(1)
                    pbar.set_postfix({'Status': f"Skipped {unique_id}"})
                    continue
                # 标记为正在处理
                IN_PROGRESS_CACHE.add(unique_id)

            try:
                os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

                # 调用后端 API
                with open(file_path, 'rb') as f:
                    response = requests.post(api_url, files={'file': f})

                if response.status_code == 200:
                    with open(target_file_path, 'wb') as f_out:
                        f_out.write(response.content)

                    with PROCESS_LOCK:
                        # 更新已处理记录
                        backend_processed_files.add(unique_id)
                        save_processed_record(PROCESSED_RECORD, backend_processed_files)

                    pbar.set_postfix({'Status': f"Processed {unique_id}"})
                else:
                    error_message = response.json().get('error', 'Unknown error')
                    log_failed_video(unique_id, error_message)
                    pbar.set_postfix({'Status': f"Failed {unique_id}"})
            except Exception as e:
                log_failed_video(unique_id, str(e))
                pbar.set_postfix({'Status': f"Error {unique_id}"})
            finally:
                # 无论成功还是失败，都从缓存中移除
                with PROCESS_LOCK:
                    IN_PROGRESS_CACHE.remove(unique_id)

            pbar.update(1)

    print(f"[Backend] Processing with {api_url} complete.")

if __name__ == '__main__':
    try:
        # 确保目标文件夹存在
        os.makedirs(TARGET_FOLDER, exist_ok=True)
        os.makedirs(FRONTEND_PROCESSED_FOLDER, exist_ok=True)

        # 加载处理记录
        backend_processed_files = load_processed_record(PROCESSED_RECORD)
        frontend_processed_files = load_processed_record(FRONTEND_PROCESSED_RECORD)
        subtitle_processed_files = load_processed_record(SUBTITLE_RECORD)

        # 获取待处理文件列表
        video_list = get_video_list()

        # 启动前端、字幕提取和后端的独立线程
        #frontend_thread = Thread(target=frontend_process, args=(video_list, frontend_processed_files))
        subtitle_thread = Thread(target=extract_subtitles,daemon=True, args=(video_list, subtitle_processed_files))
        backend_threads = []
        for api_url in BACKEND_SERVERS:
            thread = Thread(target=backend_process, args=(video_list, backend_processed_files, api_url))
            backend_threads.append(thread)
            thread.start()

        #frontend_thread.start()
        subtitle_thread.start()
        #backend_thread.start()

        #frontend_thread.join()
        subtitle_thread.join()
        for thread in backend_threads:
            thread.join()

        print("All processing complete.")
    except KeyboardInterrupt:
        print("\n[Main] Interrupt received. Stopping all processes...")
        STOP_EVENT.set()
        subtitle_thread.join()
        for thread in backend_threads:
            thread.join()
        print("[Main] All processes stopped.")
