import os
import socket
import uvicorn


def get_available_port(default_port: int = 8010) -> int:
    env_port = os.getenv("PORT")
    if env_port:
        return int(env_port)
    # Check if default_port is free
    for port in (8010, 8000, 8080, 8888):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return default_port


if __name__ == "__main__":
    port = get_available_port(8010)
    print(f"Starting Client Brain server on http://127.0.0.1:{port}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)

