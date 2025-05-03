import os
import sys
import platform
from typing import List
from invoke import task

#Activar entorno virtual
if platform.system() == "Windows":
    venv = ".\\venv\\Scripts\\Activate.ps1"
else:
    venv = "source ./venv/bin/activate"

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("REGION", "us-central1")


@task
def require_project(c):  # noqa: ANN001, ANN201
    """(Check) Require GOOGLE_CLOUD_PROJECT be defined"""
    if GOOGLE_CLOUD_PROJECT is None:
        print("GOOGLE_CLOUD_PROJECT not defined. Required for task")
        sys.exit(1)

@task
def dev(c):
    """Ejecuta la app en modo desarrollo"""
    print("🚀 Lanzando app en modo desarrollo...")
    c.run("set FLASK_ENV=development && python app.py", pty=True)







@task
def test(c):
    """Corre tests unitarios"""
    if platform.system() == "Windows":
        c.run(f"{venv}; pytest test/test_app.py")
    else:
        c.run(f"{venv} && pytest test/test_app.py")


@task
def lint(c):
    """Chequea el estilo del código"""
    c.run("flake8 app.py")


@task
def fix(c):
    """Aplica formato automático (black + isort)"""
    c.run("black . --force-exclude venv")
    c.run("isort . --profile google")


@task(pre=[require_project])
def build(c):
    """Construye la imagen y la sube a Google Cloud Build"""
    image_uri = f"{REGION}-docker.pkg.dev/{GOOGLE_CLOUD_PROJECT}/samples/microservice-template:manual"
    c.run(f"gcloud builds submit --pack image={image_uri}")


@task(pre=[require_project])
def deploy(c):
    """Despliega en Cloud Run"""
    image_uri = f"{REGION}-docker.pkg.dev/{GOOGLE_CLOUD_PROJECT}/samples/microservice-template:manual"
    c.run(
        f"gcloud run deploy microservice-template "
        f"--image {image_uri} "
        f"--platform managed --region {REGION} --allow-unauthenticated"
    )

@task
def setup(c):
    """Crea entorno virtual e instala dependencias"""
    print("🔧 Creando entorno virtual...")
    c.run("python -m venv venv", warn=True)

    print("📦 Instalando dependencias...")
    if platform.system() == "Windows":
        c.run(".\\venv\\Scripts\\pip install -r requirements.txt")
    else:
        c.run("venv/bin/pip install -r requirements.txt")


@task
def setup_test(c):
    """Instala dependencias de test"""
    if platform.system() == "Windows":
        c.run(".\\venv\\Scripts\\pip install -r requirements-test.txt")
    else:
        c.run("venv/bin/pip install -r requirements-test.txt")

@task
def require_venv(c, test_requirements=False, quiet=True):  # noqa: ANN001, ANN201
    """(Check) Require that virtualenv is setup, requirements installed"""

    c.run("python -m venv venv")
    quiet_param = " -q" if quiet else ""

    with c.prefix(venv):
        c.run(f"pip install -r requirements.txt {quiet_param}")

        if test_requirements:
            c.run(f"pip install -r requirements-test.txt {quiet_param}")


@task
def require_venv_test(c):  # noqa: ANN001, ANN201
    """(Check) Require that virtualenv is setup, requirements (incl. test) installed"""
    require_venv(c, test_requirements=True)


@task
def setup_virtualenv(c):  # noqa: ANN001, ANN201
    """Create virtualenv, and install requirements, with output"""
    require_venv(c, test_requirements=True, quiet=False)


@task(pre=[require_venv])
def start(c):  # noqa: ANN001, ANN201
    """Start the web service"""
    with c.prefix(venv):
        c.run("python app.py")


@task(pre=[require_venv])
def dev(c):  # noqa: ANN001, ANN201
    """Start the web service in a development environment, with fast reload"""
    with c.prefix(venv):
        c.run("FLASK_ENV=development python app.py")


@task(pre=[require_venv])
def lint(c):  # noqa: ANN001, ANN201
    """Run linting checks"""
    with c.prefix(venv):
        local_names = _determine_local_import_names(".")
        c.run(
            "flake8 --exclude venv "
            "--max-line-length=88 "
            "--import-order-style=google "
            f"--application-import-names {','.join(local_names)} "
            "--ignore=E121,E123,E126,E203,E226,E24,E266,E501,E704,W503,W504,I202"
        )


def _determine_local_import_names(start_dir: str) -> List[str]:
    """Determines all import names that should be considered "local".
    This is used when running the linter to insure that import order is
    properly checked.
    """
    file_ext_pairs = [os.path.splitext(path) for path in os.listdir(start_dir)]
    return [
        basename
        for basename, extension in file_ext_pairs
        if extension == ".py"
        or os.path.isdir(os.path.join(start_dir, basename))
        and basename not in ("__pycache__")
    ]


@task(pre=[require_venv])
def fix(c):  # noqa: ANN001, ANN201
    """Apply linting fixes"""
    with c.prefix(venv):
        c.run("black *.py **/*.py --force-exclude venv")
        c.run("isort --profile google *.py **/*.py")


@task(pre=[require_project])
def build(c):  # noqa: ANN001, ANN201
    """Build the service into a container image"""
    c.run(
        f"gcloud builds submit --pack "
        f"image={REGION}-docker.pkg.dev/{GOOGLE_CLOUD_PROJECT}/samples/microservice-template:manual"
    )


@task(pre=[require_project])
def deploy(c):  # noqa: ANN001, ANN201
    """Deploy the container into Cloud Run (fully managed)"""
    c.run(
        "gcloud run deploy microservice-template "
        f"--image {REGION}-docker.pkg.dev/{GOOGLE_CLOUD_PROJECT}/samples/microservice-template:manual "
        f"--platform managed --region {REGION}"
    )


@task(pre=[require_venv_test])
def test(c):  # noqa: ANN001, ANN201
    """Run unit tests"""
    with c.prefix(venv):
        c.run("pytest test/test_app.py")


@task(pre=[require_venv_test])
def system_test(c):  # noqa: ANN001, ANN201
    """Run system tests"""
    with c.prefix(venv):
        c.run("pytest test/test_system.py")
