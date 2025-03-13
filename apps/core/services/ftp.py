#!/usr/bin/env python3
import ftplib
import logging
import os

logger = logging.getLogger(__name__)


class FtpUploader:
    def __init__(self, host, user, password, port=21):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.ftp = None

    def connect(self):
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.user, self.password)
            return True
        except ftplib.all_errors as e:
            logger.error(f"Error de conexión FTP: {e}")
            return False

    def disconnect(self):
        if self.ftp:
            self.ftp.quit()
            self.ftp = None

    def create_directory(self, directory_path):
        directory_path = directory_path.replace("\\", "/")
        dirs = [d for d in directory_path.split("/") if d]

        current_dir = ""
        for directory in dirs:
            if not current_dir:
                current_dir = directory
            else:
                current_dir = f"{current_dir}/{directory}"

            try:
                self.ftp.cwd(current_dir)
            except ftplib.error_perm:
                try:
                    self.ftp.mkd(current_dir)
                    self.ftp.cwd(current_dir)
                except ftplib.error_perm:
                    raise

        self.ftp.cwd("/")

    def upload_file(self, local_file_path, remote_directory, remote_filename=None):
        if not os.path.exists(local_file_path):
            return False

        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)

        try:
            if not self.connect():
                return False

            self.create_directory(remote_directory)
            self.ftp.cwd(remote_directory)

            with open(local_file_path, "rb") as file:
                self.ftp.storbinary(f"STOR {remote_filename}", file)

            return True

        except Exception as e:
            logger.error(f"Error: {e}")
            return False

        finally:
            self.disconnect()
