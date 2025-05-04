from invoke import task
import os


def get_env(var_name, default=None):
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Environment variable '{var_name}' is not set and no default was provided.")
    return value


@task
def setup_registry(c):
    """Crea el repositorio en Artifact Registry y da permisos"""
    project = get_env("GOOGLE_CLOUD_PROJECT")
    region = get_env("REGION")
    repo = get_env("REPOSITORY")
    user = get_env("ARTIFACT_REGISTRY_USER")

    print(f"🗃️ Verificando repositorio '{repo}' en {region}...")
    result = c.run(
        f"gcloud artifacts repositories list --location={region} --project={project} --filter=name:{repo}",
        hide=True,
        warn=True,
    )

    if repo not in result.stdout:
        print("📦 Repositorio no encontrado, creándolo...")
        # Aquí no usamos comillas simples para evitar errores en PowerShell
        c.run(
            f'gcloud artifacts repositories create {repo} '
            f'--repository-format=docker '
            f'--location={region} '
            f'--description="Docker repo for backend microservices"',
            pty=False
        )
    else:
        print("📦 El repositorio ya existe.")

    print(f"🛡️ Asignando permisos a {user} para subir imágenes...")
    c.run(
        f"gcloud projects add-iam-policy-binding {project} "
        f'--member="user:{user}" '
        f'--role="roles/artifactregistry.writer"',
        warn=True,
        pty=False
    )


@task
def build_and_push(c):
    """Build and push Docker image to Artifact Registry."""
    project = get_env("GOOGLE_CLOUD_PROJECT")
    region = get_env("REGION")
    repo = get_env("REPOSITORY")
    image_name = get_env("IMAGE_NAME")
    tag = get_env("IMAGE_TAG", "latest")

    image_path = f"{region}-docker.pkg.dev/{project}/{repo}/{image_name}:{tag}"
    print(f"🔨 Construyendo imagen con tag: {image_path}...")

    c.run(f"docker build -t {image_path} .", pty=False)
    print("🚀 Haciendo push de la imagen a Artifact Registry...")
    c.run(f"docker push {image_path}", pty=False)
    print("✅ Imagen subida correctamente.")


@task
def deploy(c):
    """Despliega la imagen a Cloud Run"""
    import re

    project = get_env("GOOGLE_CLOUD_PROJECT")
    region = get_env("REGION")
    repo = get_env("REPOSITORY")
    image_name = get_env("IMAGE_NAME")
    tag = get_env("IMAGE_TAG", "latest")
    service_name = get_env("SERVICE_NAME")

    # Validación de nombre
    if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", service_name):
        raise ValueError(
            f"❌ Invalid SERVICE_NAME '{service_name}'. It must only contain lowercase letters, numbers, "
            f"and hyphens (-), must not begin or end with a hyphen, and be <= 63 characters."
        )

    image_path = f"{region}-docker.pkg.dev/{project}/{repo}/{image_name}:{tag}"
    print(f"🚀 Desplegando {image_path} en Cloud Run como servicio '{service_name}'...")

    c.run(
        f"gcloud run deploy {service_name} "
        f"--image={image_path} "
        f"--platform=managed "
        f"--region={region} "
        f"--allow-unauthenticated",
        pty=False
    )
    print("✅ Servicio desplegado correctamente.")

