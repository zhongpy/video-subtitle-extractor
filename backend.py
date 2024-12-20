from flask import Flask, request, jsonify, send_file
import os
from moviepy.video.io.VideoFileClip import VideoFileClip
from backend.main import SubtitleRemover

app = Flask(__name__)

# 创建必要文件夹
TEMP_FOLDER = 'temp'
PROCESSED_FOLDER = 'processed'
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


def compress_video(input_path, output_path, target_bitrate="1000k"):
    """
    使用 moviepy 压缩视频。
    :param input_path: 输入视频路径
    :param output_path: 输出压缩后的视频路径
    :param target_bitrate: 目标比特率，默认为 1000k。
    """
    try:
        # 打开视频文件
        clip = VideoFileClip(input_path)

        # 使用 write_videofile 方法指定目标比特率进行压缩
        clip.write_videofile(
            output_path,
            codec="libx264",  # 使用 H.264 编码
            bitrate=target_bitrate,
            audio_codec="aac",  # 保留音频
            preset="medium"  # 速度/质量平衡
        )
        clip.close()
    except Exception as e:
        raise RuntimeError(f"Video compression failed: {str(e)}")


def process_video(video_path, output_path):
    """
    使用 SubtitleRemover 处理视频，完成字幕移除并压缩视频。
    """
    subtitle_remover = SubtitleRemover(video_path)
    subtitle_remover.run()

    # 获取处理后的视频路径
    processed_video_path = subtitle_remover.video_out_name

    # 确保处理后的视频存在
    if not os.path.exists(processed_video_path):
        raise FileNotFoundError("Subtitle removal failed. Processed file not found.")

    # 添加压缩步骤
    compressed_video_path = output_path  # 直接将压缩结果写入输出路径
    compress_video(processed_video_path, compressed_video_path)

    return compressed_video_path


@app.route('/process', methods=['POST'])
def process():
    """
    API 接口：接收文件，处理后返回处理后的视频文件。
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # 创建临时文件
    input_path = os.path.join(TEMP_FOLDER, file.filename)

    # 保存上传的文件
    file.save(input_path)

    try:
        # 调用视频处理函数
        compressed_video_path = process_video(input_path, os.path.join(PROCESSED_FOLDER, file.filename))

        # 返回处理后的视频
        return send_file(compressed_video_path, as_attachment=True)

    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        return jsonify({'error': f"Unexpected error occurred: {str(e)}"}), 500

    finally:
        # 清理临时文件
        if os.path.exists(input_path):
            os.remove(input_path)


if __name__ == '__main__':
    print("Backend service running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
