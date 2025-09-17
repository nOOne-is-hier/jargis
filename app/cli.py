# app/cli.py
import sys
import subprocess
import uvicorn


def api():
    uvicorn.run("app.main:app", reload=True, host="127.0.0.1", port=8000)


def db():
    # import 시 실행되게 되어 있으면 이걸로 충분
    import app.bootstrap_db  # noqa: F401


def ui():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "ui/Home.py",
            "--server.port",
            "8501",
        ],
        check=True,
    )
