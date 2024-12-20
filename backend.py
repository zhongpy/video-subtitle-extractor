from flask import Flask, request, jsonify, send_file
import os
import shutil
from backend.main import SubtitleRemover  # 导入SubtitleRemover类

app = Flask(__name__)

# 模拟视频处理函数
def process_video(video_path, output_path):
    """
    模拟处理视频的函数，将视频从输入路径复制到输出路径。
    """
    subtitle_remover = SubtitleRemover(video_path)
    subtitle_remover.run()

    # 获取处理后的视频路径
    processed_video_path = subtitle_remover.video_out_name

    # 确保处理后的视频存在
    if not os.path.exists(processed_video_path):
        raise FileNotFoundError("Subtitle removal failed. Processed file not found.")

    # 这里可以添加实际的视频处理逻辑
    shutil.copyfile(processed_video_path, output_path)

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

    # 创建临时文件夹和处理后文件夹
    os.makedirs('temp', exist_ok=True)
    os.makedirs('processed', exist_ok=True)

    input_path = os.path.join('temp', file.filename)
    output_path = os.path.join('processed', file.filename)

    # 保存上传的文件
    file.save(input_path)

    try:
        # 调用处理函数
        process_video(input_path, output_path)

        # 将处理后的文件发送给客户端
        response = send_file(output_path, as_attachment=True)

        # 清理处理后的文件
        os.remove(output_path)

        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # 清理临时文件
        if os.path.exists(input_path):
            os.remove(input_path)

if __name__ == '__main__':
    # 确保启动前清理并创建必要的文件夹
    os.makedirs('temp', exist_ok=True)
    os.makedirs('processed', exist_ok=True)
    print("Backend service running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
