# run.py
from app import app

if __name__ == '__main__':
    print("=" * 50)
    print("校园图书借阅管理系统启动中...")
    print("=" * 50)
    print(f"访问地址: http://localhost:5000")
    print(f"测试账户: admin / 123456")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)