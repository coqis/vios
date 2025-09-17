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

from functools import cached_property

import paramiko


class SSHClient(object):
    def __init__(self, username: str, password: str, host: str, port: int = 22, pkey_path=None):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.pkey_path = pkey_path

    def upload(self, local_path, remote_path):
        """上传文件"""
        try:
            self.__sftp.put(local_path, remote_path)
            print(f"upload successfully: {local_path} -> {remote_path}")
            return True
        except Exception as e:
            print(f"failed to upload: {e}")
            return False

    def download(self, remote_path, local_path):
        """下载文件"""
        try:
            self.__sftp.get(remote_path, local_path)
            print(f"download successfully: {remote_path} -> {local_path}")
            return True
        except Exception as e:
            print(f"failed to download: {e}")
            return False

    def run(self, command: str):
        if self.__client:
            stdin, stdout, stderr = self.__client.exec_command(command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            print(output)
            if error:
                print(error)
            # return output, error
        else:
            print("SSH client is not connected.")
            # return None, None

    def close(self):
        if self.__client:
            self.__client.close()
            print(f"Connection to {self.host}:{self.port} closed")

    @cached_property
    def __sftp(self):
        if self.__client:
            return self.__client.open_sftp()
        else:
            print("SSH client is not connected.")
            return None

    @cached_property
    def __client(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            if self.pkey_path:
                pkey = paramiko.RSAKey.from_private_key_file(self.pkey_path)
                ssh.connect(self.host, port=self.port,
                            username=self.username, pkey=pkey)
            else:
                ssh.connect(self.host, port=self.port,
                            username=self.username, password=self.password)
            print(f"Connected to {self.host}:{self.port} as {self.username}")
            return ssh
        except Exception as e:
            print(f"Failed to connect to {self.host}:{self.port} - {e}")
            return None
