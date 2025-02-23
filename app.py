from flask import Flask, jsonify, request, send_file, render_template
import os
from datetime import datetime
from urllib.parse import unquote
import time
import base64
from configparser import ConfigParser
from gevent.pywsgi import WSGIServer

config = ConfigParser()
config.read("config.ini")
config_port = config.getint("server", "port")
config_password = config.get("server", "password")

app = Flask(__name__)


def authorise(_key):
    key_1 = str(int(time.time() / 60)) + config_password
    key_2 = str(int(time.time() / 60) - 1) + config_password
    key_3 = str(int(time.time() / 60) + 1) + config_password
    try:
        _key = base64.b64decode(_key.encode("utf-8")).decode("utf-8")
        if key_1 == _key or key_2 == _key or key_3 == _key:
            return True
        return False
    except:
        return False


@app.route("/api/auth", methods=["GET"])
def auth():
    _key = request.args.get("key")
    if not _key:
        return jsonify({"success": False, "error": "参数“key”不能为空。"}), 400

    if not authorise(unquote(_key)):
        return jsonify({"success": False, "error": "无效的密钥。"}), 401
    return jsonify({"success": True, "message": "已授权。"})


@app.route("/api/fileList", methods=["GET"])
def fileList():
    path = request.args.get("path")
    if not path:
        return jsonify({"success": False, "error": "参数“path”不能为空。"}), 400
    _key = request.args.get("key")
    if not _key:
        return jsonify({"success": False, "error": "参数“key”不能为空。"}), 400

    if not authorise(unquote(_key)):
        return jsonify({"success": False, "error": "无效的密钥。"}), 401
    items = []
    try:
        path = unquote(path)
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            item_info = {
                "name": item,
                "isFolder": os.path.isdir(item_path),
                "modified": datetime.fromtimestamp(
                    os.path.getmtime(item_path)
                ).strftime("%Y-%m-%d %H:%M:%S"),
            }
            if os.path.isfile(item_path):
                item_info["size"] = os.path.getsize(item_path)
            items.append(item_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(items)


@app.route("/api/download", methods=["GET"])
def download():
    path = request.args.get("path")
    if not path:
        return render_template("error.html", error="参数“path”不能为空。"), 400
    _key = request.args.get("key")
    if not _key:
        return render_template("error.html", error="参数“key”不能为空。"), 400

    if not authorise(unquote(_key)):
        return render_template("error.html", error="无效的密钥。"), 401
    try:
        path = unquote(path)
        if not os.path.isfile(path):
            return render_template("error.html", error="文件不存在。"), 404
        return send_file(path, as_attachment=False)
    except Exception as e:
        return render_template("error.html", error=str(e))


@app.route("/api/mkdir", methods=["POST"])
def mkdir():
    path = request.args.get("path")
    name = request.args.get("name")
    _key = request.args.get("key")
    if not path:
        return jsonify({"success": False, "error": "参数“path”不能为空。"}), 400
    if not name:
        return jsonify({"success": False, "error": "参数“name”不能为空。"}), 400
    if not _key:
        return jsonify({"success": False, "error": "参数“key”不能为空。"}), 400

    if not authorise(unquote(_key)):
        return jsonify({"success": False, "error": "无效的密钥。"}), 401
    try:
        path = unquote(path)
        os.makedirs(os.path.join(path, name))
        return jsonify({"success": True, "message": "创建成功。"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload():
    path = request.args.get("path")
    _key = request.args.get("key")
    if not path:
        return jsonify({"success": False, "error": "参数“path”不能为空。"}), 400
    if not _key:
        return jsonify({"success": False, "error": "参数“key”不能为空。"}), 400

    if not authorise(unquote(_key)):
        return jsonify({"success": False, "error": "无效的密钥。"}), 401
    if os.path.isfile(os.path.join(path, request.files.get("file").filename)):
        return jsonify({"success": False, "error": "文件已存在。"}), 400
    try:
        path = unquote(path)
        file = request.files.get("file")
        if not file:
            return jsonify({"success": False, "error": "文件不能为空。"}), 400
        file.save(os.path.join(path, file.filename))
        return jsonify({"success": True, "message": "上传成功。"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")


@app.route("/auth", methods=["GET"])
def auth_redirect():
    return app.send_static_file("auth.html")


@app.route("/", methods=["GET"])
def index():
    return app.send_static_file("index.html")

print("Burger 远程文件服务已启动，访问 本机IP:" + str(config_port) + " 开始使用。")

server = WSGIServer(("0.0.0.0", config_port), app)
server.serve_forever()