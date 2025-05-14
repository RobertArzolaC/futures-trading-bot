from fabric import Connection
from invoke import task

# Configuración del servidor
REMOTE_HOST = "146.190.39.157"
REMOTE_USER = "root"
REMOTE_PROJECT_PATH = "/home/futures-trading-bot/"
GIT_REPO = "git@github.com:RobertArzolaC/futures-trading-bot.git"


@task
def deploy(c):
    """Realiza el despliegue del proyecto Django."""
    # Conectarse al servidor remoto
    print("Conectando al servidor...")
    conn = Connection(host=REMOTE_HOST, user=REMOTE_USER)

    # Cambiar al directorio del proyecto
    with conn.cd(REMOTE_PROJECT_PATH):
        print("Obteniendo los últimos cambios del repositorio...")
        conn.run("git pull origin main")

        print("Actualizando dependencias...")
        conn.run(
            "source venv/bin/activate && pip install -r requirements/production.txt"
        )

        print("Aplicando migraciones...")
        conn.run("source venv/bin/activate && python manage.py migrate")

        print("Recopilando archivos estáticos...")
        conn.run(
            "source venv/bin/activate && python manage.py collectstatic --noinput"
        )

        print("Reiniciando el servidor...")
        conn.run("sudo systemctl restart gunicorn")
        conn.run("sudo systemctl restart nginx")

    print("¡Despliegue completado con éxito!")
