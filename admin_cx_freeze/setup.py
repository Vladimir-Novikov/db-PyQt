import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"


include_files = ["data", "documentation"]
options = {
    "build_exe": {
        "include_msvcr": True,
        "build_exe": "build_admin_app",  # имя папки в которой будут файлы готовой сборки
        "include_files": include_files,
    }
}

setup(
    name="admin",
    version="1.0",
    description="admin_app",
    executables=[Executable("admin.py", base=base)],
    options=options,
)
