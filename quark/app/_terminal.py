# MIT License

# Copyright (c) 2025 YL Feng

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import os
import platform
import shutil
import subprocess


def open_terminal(command: str | None = None, cwd: str | None = None):
    """打开一个新的终端窗口

    Args:
        command (str | None, optional): 在终端中执行的命令. Defaults to None.
        cwd (str | None, optional): 指定启动路径. Defaults to None.

    Raises:
        RuntimeError: 未找到 cmd 或 PowerShell
        RuntimeError: 未检测到可用的终端程序
        RuntimeError: 不支持的系统
    """
    system = platform.system()

    # ---------- Windows ----------
    if system == "Windows":
        # 检查是否在 VSCode 内运行
        is_vscode = "VSCODE_GIT_IPC_HANDLE" in os.environ or "TERM_PROGRAM" in os.environ and "vscode" in os.environ["TERM_PROGRAM"].lower(
        )

        # 优先使用 Windows Terminal
        wt_path = shutil.which("wt")
        if wt_path:
            cmd = [wt_path]
            if cwd:
                cmd += ["-d", cwd]
            if command:
                cmd += ["powershell", "-NoExit", "-Command", command]
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return

        # 其次，如果在 VSCode 中运行，尝试通过 code CLI 打开终端
        code_path = shutil.which("code")
        if is_vscode and code_path:
            print("⚙️ 当前处于 VSCode 内部，建议使用 VSCode 终端执行。")
            subprocess.Popen(["code", "-r", "."])
            return

        # 否则，回退到 cmd 或 PowerShell
        shell = shutil.which("powershell.exe") or shutil.which("cmd.exe")
        if not shell:
            raise RuntimeError("未找到 cmd 或 PowerShell")

        if "powershell" in shell:
            args = [shell, "-NoExit"]
            if command:
                args += ["-Command", command]
        else:
            args = [shell, "/k", command or ""]

        subprocess.Popen(
            args, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)

    # ---------- macOS ----------
    elif system == "Darwin":
        if command:
            subprocess.Popen([
                "osascript", "-e",
                f'tell application "Terminal" to do script "{command}"'
            ])
        else:
            subprocess.Popen(["open", "-a", "Terminal"])

    # ---------- Linux ----------
    elif system == "Linux":
        terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
        for term in terminals:
            if shutil.which(term):
                if command:
                    subprocess.Popen(
                        [term, "--", "bash", "-c", f"{command}; exec bash"],
                        cwd=cwd
                    )
                else:
                    subprocess.Popen([term], cwd=cwd)
                break
        else:
            raise RuntimeError("未检测到可用的终端程序")

    else:
        raise RuntimeError(f"不支持的系统: {system}")
