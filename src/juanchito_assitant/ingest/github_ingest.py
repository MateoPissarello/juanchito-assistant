import asyncio
from sqlmodel import Session, select
from juanchito_assitant.db.database import get_engine, get_session
from juanchito_assitant.ingest.github_client import GitHubClient
from juanchito_assitant.agents.repo_analyzer import RepoAnalyzer
from juanchito_assitant.models.profile import PersonalProject, TrackedRepo


class GitHubIngestService:
    """Orquestador asíncrono para ingesta de repositorios desde GitHub hacia SQLite."""

    def __init__(
        self,
        github_client: GitHubClient | None = None,
        analyzer: RepoAnalyzer | None = None,
        engine=None,
        overrides: dict[str, dict] | None = None,
    ):
        self.github_client = github_client or GitHubClient()
        self.analyzer = analyzer or RepoAnalyzer()
        self.engine = engine or get_engine()
        self.overrides = overrides  # Si es None, consulta la tabla TrackedRepo en SQLite

    def get_tracked_config(self, repo_name: str, session: Session | None = None) -> dict:
        """Obtiene configuración (branch, include) desde overrides o desde SQLite (TrackedRepo)."""
        if self.overrides is not None:
            return self.overrides.get(repo_name, {})

        def _query(sess: Session) -> dict:
            item = sess.exec(select(TrackedRepo).where(TrackedRepo.name == repo_name)).first()
            if item:
                return {"branch": item.branch, "include": item.is_active}
            return {}

        if session is not None:
            return _query(session)
        with get_session(self.engine) as sess:
            return _query(sess)

    def get_active_tracked_names(self, session: Session | None = None) -> list[str]:
        """Retorna la lista de nombres de repositorios activos en SQLite."""
        def _query(sess: Session) -> list[str]:
            records = sess.exec(select(TrackedRepo).where(TrackedRepo.is_active == True)).all()
            return [r.name for r in records]

        if session is not None:
            return _query(session)
        with get_session(self.engine) as sess:
            return _query(sess)

    async def sync_repo(
        self,
        repo: dict,
        session: Session | None = None,
        force: bool = False,
    ) -> tuple[PersonalProject, bool]:
        """Inspecciona un repositorio individual.

        Verifica si hay cambios basándose en 'pushed_at' y solo invoca al LLM
        si el repositorio es nuevo, si cambió el código en GitHub o si force=True.
        Retorna (proyecto, was_updated).
        """
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        html_url = repo.get("html_url", "")
        description = repo.get("description")
        is_private = repo.get("private", False)
        is_fork = repo.get("fork", False)
        pushed_at = repo.get("pushed_at")

        # Determinar rama con soporte a overrides (ej. scraping-v2) desde SQLite
        override = self.get_tracked_config(repo_name, session=session)
        branch = override.get("branch") or repo.get("default_branch") or "main"

        # 1. Verificación previa en base de datos
        def _check_existing(sess: Session) -> PersonalProject | None:
            return sess.exec(
                select(PersonalProject).where(PersonalProject.name == repo_name)
            ).first()

        existing_proj = None
        if session is not None:
            existing_proj = _check_existing(session)
        else:
            with get_session(self.engine) as sess:
                existing_proj = _check_existing(sess)

        # Si ya existe, NO se forzó y pushed_at coincide exactamente -> omitir análisis LLM
        if (
            existing_proj
            and not force
            and existing_proj.last_pushed_at
            and existing_proj.last_pushed_at == pushed_at
        ):
            return existing_proj, False

        # 2. Inspeccionar árbol, README y manifiestos en GitHub
        ctx = await self.github_client.inspect_repo(
            owner=owner,
            repo_name=repo_name,
            branch=branch,
            html_url=html_url,
            description=description,
            is_private=is_private,
            is_fork=is_fork,
        )

        # 3. Análisis técnico y síntesis con LLM (OpenRouter / Gemini)
        analysis = await self.analyzer.analyze(ctx)

        # 4. Upsert idempotente en la base de datos
        def _persist(sess: Session) -> PersonalProject:
            existing = sess.exec(
                select(PersonalProject).where(PersonalProject.name == repo_name)
            ).first()

            if existing:
                existing.repo_url = html_url
                existing.branch = branch
                existing.description = analysis.summary or description
                existing.bullets = analysis.bullets
                existing.technologies = analysis.technologies
                existing.has_readme = analysis.has_adequate_readme
                existing.suggested_readme = analysis.suggested_readme
                existing.last_pushed_at = pushed_at
                sess.add(existing)
                project = existing
            else:
                project = PersonalProject(
                    name=repo_name,
                    repo_url=html_url,
                    branch=branch,
                    description=analysis.summary or description,
                    bullets=analysis.bullets,
                    technologies=analysis.technologies,
                    has_readme=analysis.has_adequate_readme,
                    suggested_readme=analysis.suggested_readme,
                    last_pushed_at=pushed_at,
                )
                sess.add(project)

            sess.commit()
            sess.refresh(project)
            return project

        if session is not None:
            saved = _persist(session)
        else:
            with get_session(self.engine) as sess:
                saved = _persist(sess)

        return saved, True

    async def sync_all(
        self,
        username: str = "MateoPissarello",
        visibility: str = "all",
        exclude_forks: bool = True,
        max_concurrency: int = 3,
        repo_names: list[str] | None = None,
        force: bool = False,
    ) -> list[tuple[PersonalProject, bool]]:
        """Sincroniza múltiples repositorios concurrentemente controlados por semáforo."""
        repos = await self.github_client.list_repos(
            username=username,
            visibility=visibility,
            exclude_forks=exclude_forks,
        )

        # Si no se especificó repo_names, consultar los repositorios activos en SQLite
        if repo_names is None:
            active_names = self.get_active_tracked_names()
            if active_names:
                repo_names = active_names

        # Filtrar por lista específica si se proporciona
        if repo_names:
            names_set = {n.lower() for n in repo_names}
            repos = [r for r in repos if r.get("name", "").lower() in names_set]

        # Filtrar repositorios explícitamente excluidos en configuración o SQLite
        filtered_repos = []
        for r in repos:
            name = r.get("name", "")
            if not self.get_tracked_config(name).get("include", True):
                continue
            filtered_repos.append(r)


        semaphore = asyncio.Semaphore(max_concurrency)

        async def _worker(r: dict) -> tuple[PersonalProject, bool] | None:
            async with semaphore:
                try:
                    return await self.sync_repo(r, force=force)
                except Exception as e:
                    repo_title = r.get("name", "unknown")
                    print(f"Advertencia: no se pudo sincronizar el repositorio '{repo_title}': {e}")
                    return None

        tasks = [_worker(r) for r in filtered_repos]
        results = await asyncio.gather(*tasks)
        return [res for res in results if res is not None]
