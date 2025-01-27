import os
import json
from functools import wraps
from flask import Flask, render_template, jsonify, request, abort

app = Flask(__name__)
SCHEMAS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), 'schemas'))


# 自定义JSON响应装饰器（修复端点冲突）
def json_response(func):
    @wraps(func)  # 关键修复：保留原始函数元数据
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            response = jsonify(result)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            app.logger.error(f"Error in {func.__name__}: {str(e)}")
            return jsonify({"error": "服务器内部错误", "detail": str(e)}), 500

    return wrapper

def a():
    pass

def b():
    pass

@app.route("/get_schemas")
@json_response
def get_schemas():
    """获取可用Schema列表"""
    if not os.path.exists(SCHEMAS_DIR):
        return {"error": "Schema目录不存在", "path": SCHEMAS_DIR}

    if not os.path.isdir(SCHEMAS_DIR):
        return {"error": "Schema路径不是目录", "path": SCHEMAS_DIR}

    try:
        schemas = [
            f for f in os.listdir(SCHEMAS_DIR)
            if f.endswith('.json') and os.path.isfile(os.path.join(SCHEMAS_DIR, f))
        ]
        return {"schemas": sorted(schemas)}
    except PermissionError as e:
        return {"error": "目录访问被拒绝", "detail": str(e)}, 403


@app.route("/get_schema/<schema_name>")
@json_response
def get_schema(schema_name):
    """获取指定Schema内容"""
    try:
        # 路径安全校验
        if any(c in schema_name for c in ('..', '/', '\\')):
            abort(400, description="非法文件名")

        schema_path = os.path.normpath(os.path.join(SCHEMAS_DIR, schema_name))
        if not schema_path.startswith(SCHEMAS_DIR):
            abort(400, description="路径越界访问")

        with open(schema_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                return {"error": "JSON解析失败", "detail": str(e)}, 400

    except FileNotFoundError:
        abort(404, description="Schema文件不存在")


@app.errorhandler(404)
def handle_404(e):
    return jsonify({
        "error": "资源未找到",
        "message": str(e.description)
    }), 404


@app.errorhandler(400)
def handle_400(e):
    return jsonify({
        "error": "请求参数错误",
        "message": str(e.description)
    }), 400


@app.route("/")
def index():
    """主界面"""
    return render_template("index.html")


# 应用配置
app.config.update({
    'JSON_AS_ASCII': False,
    'JSON_SORT_KEYS': False,
    'RESTFUL_JSON': {'ensure_ascii': False},
    'SECRET_KEY': os.urandom(16)
})


# CORS支持（开发环境用）
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
    return response


if __name__ == "__main__":
    # 自动创建schema目录
    os.makedirs(SCHEMAS_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)