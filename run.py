import uvicorn
import os
import socket
from app.core.config import settings
from dotenv import load_dotenv

def get_local_ip():
    """Получение локального IP-адреса для доступа по сети"""
    try:
        # Подключаемся к внешнему адресу, чтобы узнать наш IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None
if __name__ == "__main__":
    load_dotenv()

    host = os.getenv("HOST", "127.0.0.1")  
    port = int(os.getenv("PORT", 8000))
    
    if host == "0.0.0.0":
        local_ip = get_local_ip()
        print("\n" + "="*60)
        print("🚀 Сервер запущен и доступен по локальной сети!")
        print("="*60)
        print(f"📍 Локальный доступ: http://127.0.0.1:{port}")
        print(f"📍 Локальный доступ: http://localhost:{port}")
        if local_ip:
            print(f"🌐 Сетевой доступ:   http://{local_ip}:{port}")
        print(f"📚 Документация:     http://127.0.0.1:{port}/docs")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("🚀 Сервер запущен!")
        print("="*60)
        print(f"📍 Локальный доступ: http://{host}:{port}")
        print(f"📚 Документация:     http://{host}:{port}/docs")
        if host == "127.0.0.1":
            local_ip = get_local_ip()
            if local_ip:
                print(f"\n💡 Для доступа по сети установите: HOST=0.0.0.0")
                print(f"   Тогда будет доступен по адресу: http://{local_ip}:{port}")
        print("="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host=host if host != "127.0.0.1" else "0.0.0.0" if os.getenv("NETWORK_ACCESS") == "true" else "127.0.0.1",
        port=port,
        reload=True
    )

