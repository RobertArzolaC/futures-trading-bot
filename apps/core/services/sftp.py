import pysftp
from django.conf import settings


def sftp_connect_and_transfer(local_path=None, remote_path=None):
    """
    Establece una conexión SFTP y transfiere archivos.

    Args:
        local_path (str): Ruta del archivo local
        remote_path (str): Ruta del archivo en el servidor remoto

    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    try:
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        host = settings.FTP_SERVER
        username = settings.FTP_USERNAME
        password = settings.FTP_PASSWORD

        with pysftp.Connection(
            host, username=username, password=password, port=22, cnopts=cnopts
        ) as sftp:
            sftp.makedirs(remote_path)
            remote_file_path = f"{remote_path}/{local_path.split('/')[-1]}"
            sftp.put(local_path, remote_file_path)

            base_message = "File uploaded successfully to sFTP server"
            return {
                "success": True,
                "message": f"{base_message} at {host}/{remote_path}",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error uploading to sFTP: {str(e)}",
        }
