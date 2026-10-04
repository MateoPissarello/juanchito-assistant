import asyncio
from dataclasses import dataclass, field
import httpx
from juanchito_assitant.config import GITHUB_TOKEN

# Nombres estándar de archivos de manifiesto y configuración técnica
KNOWN_MANIFEST_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
    "cargo.toml",
    "go.mod",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "environment.yml",
    "pom.xml",
    "build.gradle",
}


@dataclass
class RepoContext:
    """Paquete de datos extraído de GitHub listo para ser analizado por Gemini."""

    repo_name: str
    owner: str
    branch: str = "main"
    html_url: str = ""
    description: str | None = None
    is_fork: bool = False
    is_private: bool = False
    tree_paths: list[str] = field(default_factory=list)
    readme_filename: str | None = None
    readme_content: str | None = None
    manifests: dict[str, str] = field(default_factory=dict)


class GitHubClient:
    """Cliente asíncrono para interactuar con la API REST de GitHub (públicos y privados)."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.token = token if token is not None else GITHUB_TOKEN
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, transport=self.transport)

    def _get_headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": "juanchito-assitant",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def list_repos(
        self,
        username: str | None = None,
        visibility: str = "all",
        exclude_forks: bool = True,
    ) -> list[dict]:
        """Lista repositorios del usuario.

        Si se provee token, utiliza `/user/repos` para soportar públicos y privados.
        Si no hay token, consulta `/users/{username}/repos` (solo públicos).
        """
        async with self._create_client() as client:
            if self.token:
                url = f"{self.base_url}/user/repos"
                params = {"affiliation": "owner", "visibility": visibility, "per_page": 100}
                response = await client.get(url, headers=self._get_headers(), params=params)
            else:
                if not username:
                    raise ValueError("Se requiere 'username' cuando no hay GITHUB_TOKEN configurado.")
                url = f"{self.base_url}/users/{username}/repos"
                params = {"per_page": 100, "type": "owner"}
                response = await client.get(url, headers=self._get_headers(), params=params)

            response.raise_for_status()
            repos = response.json()

        # Filtrar por username si se especificó y estamos en modo autenticado
        if username and self.token:
            repos = [
                r for r in repos if r.get("owner", {}).get("login", "").lower() == username.lower()
            ]

        # Excluir forks si aplica
        if exclude_forks:
            repos = [r for r in repos if not r.get("fork", False)]

        return repos

    async def get_repo_tree(
        self, owner: str, repo: str, branch: str = "main"
    ) -> list[dict]:
        """Obtiene el árbol recursivo de archivos del repositorio vía Git Trees API."""
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}"
        params = {"recursive": "1"}

        async with self._create_client() as client:
            response = await client.get(url, headers=self._get_headers(), params=params)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            return data.get("tree", [])

    async def get_raw_file(
        self, owner: str, repo: str, path: str, branch: str = "main"
    ) -> str | None:
        """Descarga el contenido de un archivo en crudo utilizando el endpoint de contents."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": branch}
        headers = self._get_headers(accept="application/vnd.github.raw+json")

        async with self._create_client() as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.text

    async def inspect_repo(
        self,
        owner: str,
        repo_name: str,
        branch: str = "main",
        html_url: str = "",
        description: str | None = None,
        is_private: bool = False,
        is_fork: bool = False,
    ) -> RepoContext:
        """Inspecciona un repositorio: obtiene su árbol, detecta README y extrae manifiestos."""
        tree_items = await self.get_repo_tree(owner, repo_name, branch=branch)
        blob_paths = [
            item["path"]
            for item in tree_items
            if item.get("type") == "blob" and "path" in item
        ]

        # 1. Detectar archivo README en la raíz
        readme_filename: str | None = None
        for path in blob_paths:
            parts = path.split("/")
            if len(parts) == 1 and parts[0].lower().startswith("readme"):
                readme_filename = path
                break

        readme_content: str | None = None
        if readme_filename:
            readme_content = await self.get_raw_file(owner, repo_name, readme_filename, branch=branch)

        # 2. Detectar manifiestos técnicos relevantes (máx nivel 2 de profundidad)
        manifest_paths: list[str] = []
        for path in blob_paths:
            parts = path.split("/")
            if len(parts) <= 2 and parts[-1].lower() in KNOWN_MANIFEST_NAMES:
                manifest_paths.append(path)

        # 3. Descargar manifiestos concurrentemente
        manifests: dict[str, str] = {}
        if manifest_paths:
            download_tasks = [
                self.get_raw_file(owner, repo_name, m_path, branch=branch)
                for m_path in manifest_paths
            ]
            contents = await asyncio.gather(*download_tasks, return_exceptions=True)
            for m_path, content in zip(manifest_paths, contents):
                if isinstance(content, str) and content.strip():
                    # Truncar manifiestos gigantes para cuidar tokens
                    manifests[m_path] = content[:4000]

        return RepoContext(
            repo_name=repo_name,
            owner=owner,
            branch=branch,
            html_url=html_url,
            description=description,
            is_fork=is_fork,
            is_private=is_private,
            tree_paths=blob_paths,
            readme_filename=readme_filename,
            readme_content=readme_content,
            manifests=manifests,
        )
