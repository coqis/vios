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
    """Open a new terminal window

    Args:
        command (str | None, optional): Optional shell command to run inside the terminal. Defaults to None.
        cwd (str | None, optional): Optional working directory to start the terminal in. Defaults to None.

    Supports:
        - Windows Terminal
        - VSCode integrated environment
        - PowerShell / CMD fallback
        - macOS Terminal
        - Linux terminals (GNOME, Konsole, XFCE, Xterm)

    Raises:
        RuntimeError: Neither PowerShell nor CMD found on system
        RuntimeError: Linux: no supported terminal emulator found
        RuntimeError: Unsupported platform
    """
    system = platform.system()

    # ---------- Windows ----------
    if system == "Windows":
        # Detect if running inside VSCode
        is_vscode = "VSCODE_GIT_IPC_HANDLE" in os.environ or "TERM_PROGRAM" in os.environ and "vscode" in os.environ["TERM_PROGRAM"].lower(
        )

        # Prefer Windows Terminal if available
        wt_path = shutil.which("wt")
        if wt_path:
            cmd = [wt_path]
            if cwd:
                cmd += ["-d", cwd]
            if command:
                cmd += ["powershell", "-NoExit", "-Command", command]
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return

        # If inside VSCode, suggest using VSCode's terminal
        code_path = shutil.which("code")
        if is_vscode and code_path:
            print(
                "⚙️ Currently running inside VSCode; using VSCode terminal is recommended.")
            subprocess.Popen(["code", "-r", "."])
            return

        # Otherwise fallback to PowerShell or CMD
        shell = shutil.which("powershell.exe") or shutil.which("cmd.exe")
        if not shell:
            raise RuntimeError("Neither PowerShell nor CMD found on system.")

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
            command = f'cd {cwd};{command}' if cwd else command
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
            raise RuntimeError("Linux: no supported terminal emulator found")

    else:
        raise RuntimeError(f"Unsupported platform: {system}")
