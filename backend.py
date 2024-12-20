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


def compress_video(input_path, output_path, target_size_mb=20, resolution=(720, 1280), fps=30):
    """
    使用 moviepy 压缩视频。
    """
    try:
        clip = VideoFileClip(input_path)
        duration_seconds = clip.duration
        target_bitrate = (target_size_mb * 8 * 1024 * 1024) / duration_seconds
        target_bitrate = f"{int(target_bitrate / 1000)}k"

        resized_clip = clip.resize(height=resolution[1]).set_fps(fps)
        resized_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            bitrate=target_bitrate,
            preset="medium"
        )
        clip.close()
    except Exception as e:
        raise RuntimeError(f"Video compression failed: {str(e)}")


def process_video(video_path, output_path):
    """
    使用 SubtitleRemover 处理视频，并进行压缩。
    """
    subtitle_area=(0.64375, 0.1625, 0.0, 1.0)
    subtitle_remover = SubtitleRemover(video_path,subtitle_area)
    subtitle_remover.run()

    processed_video_path = subtitle_remover.video_out_name
    if not os.path.exists(processed_video_path):
        raise FileNotFoundError("Subtitle removal failed. Processed file not found.")

    compress_video(processed_video_path, output_path, target_size_mb=20, resolution=(720, 1280), fps=30)
    return output_path


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
