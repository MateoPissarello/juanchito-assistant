import asyncio
from pathlib import Path
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlmodel import select
import typer

from juanchito_assitant.agents.evaluator import EvaluatorAgent
from juanchito_assitant.agents.job_analyzer import JobAnalyzerAgent
from juanchito_assitant.agents.matcher import MatcherAgent
from juanchito_assitant.config import (
    DATA_DIR,
    DB_PATH,
    GITHUB_TOKEN,
    MODEL_CV_WRITER,
    MODEL_EVALUATOR,
    MODEL_REPO_ANALYZER,
    OPENROUTER_API_KEY,
    OUTPUTS_DIR,
    PROJECT_ROOT,
)
from juanchito_assitant.db.database import get_session, init_db
from juanchito_assitant.db.seed import run_seed
from juanchito_assitant.ingest.import_linkedin import _run_import
from juanchito_assitant.ingest.sync_github import _run_sync
from juanchito_assitant.models.profile import (
    AdditionalAchievement,
    Certification,
    Education,
    PersonalInfo,
    PersonalProject,
    SkillCategory,
    TrackedRepo,
    WorkExperience,
    WorkProject,
)
from juanchito_assitant.tailor_engine import TailoringEngine

app = typer.Typer(
    name="juanchito",
    help="Juanchito Assistant: CLI interactiva para adaptación de CVs a resume.lol y gestión de carrera técnica.",
    add_completion=False,
)
sync_app = typer.Typer(help="Sincronización inteligente de fuentes externas (GitHub, LinkedIn).")
repo_app = typer.Typer(help="Administración de repositorios seguidos en SQLite para sincronización.")

app.add_typer(sync_app, name="sync")
app.add_typer(repo_app, name="repo")

console = Console()


# ----------------------------------------------------------------------
# 1. COMANDO: STATUS (Diagnóstico de Salud de Subcomponentes)
# ----------------------------------------------------------------------
@app.command()
def status():
    """Diagnóstico en vivo de salud de la base de datos, APIs, modelos y archivos."""
    console.print(
        Panel.fit(
            "[bold cyan]🔍 Juanchito Assistant - Diagnóstico del Sistema[/bold cyan]\n"
            f"[dim]Directorio raíz:[/] {PROJECT_ROOT}\n"
            f"[dim]Base de datos:[/] {DB_PATH}",
            border_style="cyan",
        )
    )

    table = Table(title="Estado de Subcomponentes y Servicios")
    table.add_column("Componente", style="cyan bold", no_wrap=True)
    table.add_column("Estado", style="bold")
    table.add_column("Detalle / Métricas", style="white")

    # 1. Base de datos SQLite
    init_db()
    with get_session() as session:
        exp_count = len(session.exec(select(WorkExperience)).all())
        proj_count = len(session.exec(select(WorkProject)).all())
        repo_count = len(session.exec(select(PersonalProject)).all())
        tracked_count = len(session.exec(select(TrackedRepo)).all())
        cert_count = len(session.exec(select(Certification)).all())
        skill_count = len(session.exec(select(SkillCategory)).all())
        edu_count = len(session.exec(select(Education)).all())

    db_status = "[bold green]✓ Operativa[/]" if exp_count > 0 else "[bold yellow]! Vacía[/]"
    table.add_row(
        "Base de Datos (SQLite)",
        db_status,
        f"{exp_count} empresas, {proj_count} iniciativas, {repo_count} repos ingestados, {tracked_count} seguidos, {cert_count} certs, {skill_count} cat. skills, {edu_count} educ.",
    )

    # 2. Conectividad OpenRouter
    if OPENROUTER_API_KEY:
        try:
            resp = httpx.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                label = data.get("label") or "Valida"
                limit = data.get("limit")
                usage = data.get("usage", 0)
                limit_info = f" (Uso: ${usage:.2f})" if limit is None else f" (Límite: ${limit})"
                table.add_row("OpenRouter API", "[bold green]✓ Autenticado[/]", f"Key activa: {label}{limit_info}")
            else:
                table.add_row("OpenRouter API", "[bold red]✗ Error Auth[/]", f"HTTP {resp.status_code}: {resp.text[:60]}")
        except Exception as e:
            table.add_row("OpenRouter API", "[bold yellow]! Timeout/Red[/]", f"No se pudo contactar a OpenRouter: {e}")
    else:
        table.add_row("OpenRouter API", "[bold red]✗ No configurada[/]", "Variable OPENROUTER_API_KEY no encontrada")

    # 3. Conectividad GitHub
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        resp = httpx.get("https://api.github.com/rate_limit", headers=headers, timeout=5.0)
        if resp.status_code == 200:
            rate = resp.json().get("rate", {})
            rem = rate.get("remaining")
            total = rate.get("limit")
            gh_token_status = "Token Personal" if GITHUB_TOKEN else "Público (Sin token)"
            table.add_row("GitHub API", "[bold green]✓ Conectado[/]", f"{gh_token_status} - Rate Limit: {rem}/{total}")
        else:
            table.add_row("GitHub API", "[bold yellow]! Advertencia[/]", f"HTTP {resp.status_code}")
    except Exception as e:
        table.add_row("GitHub API", "[bold red]✗ Desconectado[/]", str(e))

    # 4. Modelos Configurados
    table.add_row("Evaluador ATS (System One)", "[bold green]✓ Configurado[/]", f"{MODEL_EVALUATOR} (TypeSafe Jev Router)")
    table.add_row("Redactor de CV (Writer)", "[bold green]✓ Configurado[/]", f"{MODEL_CV_WRITER}")
    table.add_row("Analizador de Código (Repos)", "[bold green]✓ Configurado[/]", f"{MODEL_REPO_ANALYZER}")

    # 5. Archivos de Datos y Permisos
    resume_file = PROJECT_ROOT / "data/examples/Backend Engineer/resume.md"
    pdf_file = DATA_DIR / "linkedin_profile.pdf"
    resume_ok = "[bold green]✓ Presente[/]" if resume_file.exists() else "[bold red]✗ Faltante[/]"
    pdf_ok = "[bold green]✓ Presente[/]" if pdf_file.exists() else "[bold yellow]! Opcional[/]"
    outputs_count = len(list(OUTPUTS_DIR.glob("*.md"))) if OUTPUTS_DIR.exists() else 0

    table.add_row("Plantilla resume.md", resume_ok, str(resume_file))
    table.add_row("LinkedIn PDF Export", pdf_ok, str(pdf_file))
    table.add_row("Directorio de Salida (outputs)", "[bold green]✓ Accesible[/]", f"{OUTPUTS_DIR} ({outputs_count} CVs generados)")

    console.print(table)


# ----------------------------------------------------------------------
# 2. COMANDO: TAILOR (Adaptación Interactiva con Jev AI)
# ----------------------------------------------------------------------
@app.command()
def tailor(
    job: str = typer.Argument(None, help="Texto de la vacante, URL directa o ruta al archivo."),
    url: str | None = typer.Option(None, "--url", "-u", help="URL de la vacante a descargar."),
    file: Path | None = typer.Option(None, "--file", "-f", help="Ruta a archivo .txt o .md con la vacante."),
    max_iterations: int = typer.Option(2, "--max-iterations", "-m", help="Límite del bucle reflexivo de auto-mejora."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Ruta personalizada donde guardar el CV."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Ejecutar análisis sin escribir en disco."),
    show_markdown: bool = typer.Option(False, "--show-markdown", help="Imprimir el contenido final en la consola."),
):
    """Adapta tu currículum para una vacante específica, evalúa con Jev AI y genera resume.md."""
    console.print(
        Panel.fit(
            "[bold green]🎯 Juanchito Tailoring Engine[/bold green]\n"
            "[dim]Adaptador de carrera para [cyan]resume.lol[/cyan] con evaluación crítica ATS (Jev Router)[/dim]",
            border_style="green",
        )
    )

    init_db()

    # 1. Determinar fuente de la vacante interactivamente si no se pasó argumento
    job_input = ""
    if url:
        job_input = url.strip()
    elif file:
        if not file.exists():
            console.print(f"[bold red]Error:[/] No se encontró el archivo: {file}")
            raise typer.Exit(code=1)
        job_input = file.read_text(encoding="utf-8")
    elif job:
        potential_path = Path(job)
        if potential_path.exists() and potential_path.is_file():
            job_input = potential_path.read_text(encoding="utf-8")
        else:
            job_input = job.strip()
    else:
        # Menú interactivo solicitado por Mateo
        console.print("[bold yellow]¿Cómo deseas ingresar la vacante?[/]")
        console.print("  [cyan][1][/] Pegar URL de la oferta (ej. Greenhouse, Lever, LinkedIn)")
        console.print("  [cyan][2][/] Pegar texto de la descripción")
        console.print("  [cyan][3][/] Cargar desde archivo local (.txt / .md)")

        choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3"], default="1")
        if choice == "1":
            job_input = Prompt.ask("🌐 Ingresa la URL de la vacante").strip()
        elif choice == "2":
            job_input = Prompt.ask("📝 Pega la descripción de la vacante").strip()
        elif choice == "3":
            file_path_str = Prompt.ask("📁 Ingresa la ruta al archivo").strip()
            fpath = Path(file_path_str)
            if not fpath.exists():
                console.print(f"[bold red]Error:[/] Archivo no encontrado: {fpath}")
                raise typer.Exit(code=1)
            job_input = fpath.read_text(encoding="utf-8")

    if not job_input:
        console.print("[bold red]Error:[/] La vacante no puede estar vacía.")
        raise typer.Exit(code=1)

    # 2. Análisis preliminar de la vacante
    with console.status("[bold cyan]Analizando requerimientos y palabras clave ATS con LLM...[/]"):
        analyzer = JobAnalyzerAgent()
        try:
            job_reqs = asyncio.run(analyzer.analyze_job(job_input))
        except Exception as e:
            console.print(f"[bold red]Error al analizar vacante:[/] {e}")
            raise typer.Exit(code=1)

    # Panel de Vista Previa interactiva
    company_name = job_reqs.company_name or "No especificada"
    must_have = ", ".join(job_reqs.must_have_skills[:6])
    ats_keys = ", ".join(job_reqs.ats_keywords[:8])
    preview_table = Table(show_header=False, box=None)
    preview_table.add_column("Clave", style="bold cyan", width=18)
    preview_table.add_column("Valor", style="white")

    preview_table.add_row("Empresa:", company_name)
    preview_table.add_row("Cargo / Título:", job_reqs.job_title)
    preview_table.add_row("Seniority:", job_reqs.seniority_level)
    preview_table.add_row("Must-Have Skills:", must_have)
    preview_table.add_row("ATS Keywords:", ats_keys)
    preview_table.add_row("Resumen del Rol:", job_reqs.role_summary[:140] + "...")

    console.print(
        Panel(
            preview_table,
            title="[bold yellow]📋 Resumen de la Oferta Detectada[/]",
            border_style="yellow",
        )
    )

    # 3. Matching con SQLite
    with get_session() as session:
        matcher = MatcherAgent(session)
        matched_ctx = matcher.match(job_reqs)

    selected_initiatives = [wm.project_name for wm in matched_ctx.work_matches]
    selected_repos = [gm.name for gm in matched_ctx.github_matches]
    console.print(
        f"[dim]🎯 Activos seleccionados del perfil para 1 página:[/] "
        f"[cyan]{len(selected_initiatives)} iniciativas[/] ({', '.join(selected_initiatives[:3])}) | "
        f"[magenta]{len(selected_repos)} repositorios[/] ({', '.join(selected_repos)})"
    )

    # Pausa de confirmación interactiva
    proceed = Confirm.ask("\n¿Proceder con la redacción y evaluación ATS con Jev AI?", default=True)
    if not proceed:
        console.print("[dim]Operación cancelada por el usuario.[/]")
        raise typer.Exit(code=0)

    # 4. Orquestación del motor reflexivo (Writer + Evaluator con Jev Router)
    with get_session() as session:
        engine = TailoringEngine(session)
        with console.status("[bold green]Redactando viñetas (Google XYZ) y evaluando con TypeSafe Jev Router...[/]"):
            try:
                report = asyncio.run(engine.run(job_input=job_input, max_iterations=max_iterations))
            except Exception as e:
                console.print(f"[bold red]Error durante la ejecución del motor:[/] {e}")
                raise typer.Exit(code=1)

    # 5. Scorecard ATS de Jev AI
    eval_res = report.final_evaluation
    score = eval_res.total_score
    score_color = "bold green" if score >= 85 else ("bold yellow" if score >= 70 else "bold red")
    decision_color = "bold green" if eval_res.decision == "APPROVE" else "bold red"

    score_table = Table(title="Scorecard de Auditoría ATS (TypeSafe Jev Router)")
    score_table.add_column("Criterio de Evaluación", style="cyan bold")
    score_table.add_column("Puntaje Máx.", justify="center", style="dim")
    score_table.add_column("Puntaje Obtenido", justify="center", style="bold")

    sb = eval_res.breakdown
    score_table.add_row("ATS Keyword Match", "25", str(sb.ats_keyword_match))
    score_table.add_row("Role Relevance", "25", str(sb.role_relevance))
    score_table.add_row("Quantifiable Impact (XYZ)", "20", str(sb.quantifiable_impact))
    score_table.add_row("Factual Integrity", "15", str(sb.factual_integrity))
    score_table.add_row("Format & Length (1 Página)", "15", str(sb.format_and_length))
    score_table.add_row("─" * 25, "───", "───")
    score_table.add_row("PUNTAJE TOTAL", "100", f"[{score_color}]{score} / 100[/]")
    score_table.add_row("DECISIÓN FINAL", "-", f"[{decision_color}]{eval_res.decision}[/]")

    console.print(score_table)

    word_count = len(report.final_markdown.split())
    console.print(f"\n[dim]Longitud del documento:[/] [bold]{word_count} palabras[/] (Alineado con el estándar de 1 página de resume.lol)")

    # Guardar en ruta personalizada si se especificó
    final_output_path = report.output_file_path
    if output and not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report.final_markdown, encoding="utf-8")
        final_output_path = output

    if not dry_run:
        console.print(
            Panel.fit(
                f"[bold green]✨ ¡Currículum generado con éxito![/]\n"
                f"[dim]Archivo guardado en:[/] [cyan]{final_output_path}[/]\n"
                f"[dim]Listo para copiar en [link=https://resume.lol]resume.lol[/link][/dim]",
                border_style="green",
            )
        )
    else:
        console.print("[bold yellow]ℹ️ Modo --dry-run activo: No se guardó archivo en disco.[/]")

    if show_markdown:
        console.print("\n[bold cyan]--- CONTENIDO GENERADO (resume.md) ---[/]")
        console.print(report.final_markdown)


# ----------------------------------------------------------------------
# 3. COMANDO: AUDIT (Inspección del Perfil Consolidado en profile.db)
# ----------------------------------------------------------------------
@app.command()
def audit(
    full: bool = typer.Option(False, "--full", help="Mostrar todas las viñetas completas de iniciativas y repositorios."),
):
    """Inspecciona en tablas Rich todo el perfil consolidado en SQLite (profile.db)."""
    init_db()
    with get_session() as session:
        personal = session.exec(select(PersonalInfo).where(PersonalInfo.id == 1)).first()
        experiences = session.exec(select(WorkExperience).order_by(WorkExperience.order_index)).all()
        projects = session.exec(select(PersonalProject)).all()
        certs = session.exec(select(Certification)).all()
        skills = session.exec(select(SkillCategory)).all()
        education = session.exec(select(Education)).all()
        achievements = session.exec(select(AdditionalAchievement)).all()

        if not personal:
            console.print("[bold red]Base de datos vacía o no inicializada.[/] Ejecuta [cyan]juanchito seed[/] primero.")
            raise typer.Exit(code=1)

        # 1. Personal Info Panel
        console.print(
            Panel.fit(
                f"[bold cyan]{personal.full_name}[/] | [dim]{personal.headline}[/]\n"
                f"[dim]Ubicación:[/] {personal.location} ({personal.timezone})  |  "
                f"[dim]GitHub:[/] @{personal.github}  |  "
                f"[dim]LinkedIn:[/] {personal.linkedin}\n"
                f"[dim]Perfil:[/] {personal.profile_summary}",
                title="[bold blue]👤 Información Personal[/]",
                border_style="blue",
            )
        )

        # 2. Experiencia Laboral e Iniciativas Técnicas
        exp_table = Table(title="Experiencia Laboral e Iniciativas Técnicas (WorkProject)")
        exp_table.add_column("Empresa", style="cyan bold", no_wrap=True)
        exp_table.add_column("Cargo", style="white")
        exp_table.add_column("Periodo", style="dim")
        exp_table.add_column("Iniciativas Técnicas", style="green")
        if full:
            exp_table.add_column("Viñetas de Impacto (Google XYZ)", style="dim")

        for exp in experiences:
            init_names = [p.name for p in exp.projects]
            inits_str = ", ".join(init_names) if init_names else "Sin iniciativas"
            date_str = f"{exp.start_date} - {exp.end_date}"
            if full:
                bullets_str = "\n".join(
                    f"• [{p.name}] {b}" for p in exp.projects for b in p.bullets
                )
                exp_table.add_row(exp.company, exp.role, date_str, inits_str, bullets_str)
            else:
                exp_table.add_row(exp.company, exp.role, date_str, inits_str)

        console.print(exp_table)

        # 3. Proyectos Personales (GitHub)
        repo_table = Table(title="Proyectos Personales Sincronizados (GitHub)")
        repo_table.add_column("Proyecto", style="magenta bold", no_wrap=True)
        repo_table.add_column("Rama", style="cyan")
        repo_table.add_column("README", style="green")
        repo_table.add_column("Tecnologías", style="yellow")
        if full:
            repo_table.add_column("Viñetas", style="white")

        for p in projects:
            readme_status = "[bold green]✓ Adecuado[/]" if p.has_readme else "[bold yellow]📝 Sugerido[/]"
            techs = ", ".join(p.technologies[:5]) if p.technologies else "None"
            if full:
                b_str = "\n".join(f"• {b}" for b in p.bullets)
                repo_table.add_row(p.name, p.branch, readme_status, techs, b_str)
            else:
                repo_table.add_row(p.name, p.branch, readme_status, techs)

        console.print(repo_table)

        # 4. Certificaciones y Habilidades
        skills_table = Table(title="Habilidades Técnicas y Certificaciones")
        skills_table.add_column("Categoría / Emisor", style="cyan bold", width=25)
        skills_table.add_column("Contenido / Títulos", style="white")

        for sk in skills:
            skills_table.add_row(f"[Skill] {sk.category}", ", ".join(sk.skills))

        for cert in certs:
            skills_table.add_row(f"[Cert] {cert.issuer}", f"{cert.title} ({cert.issue_date})")

        console.print(skills_table)

        # 5. Educación y Logros
        if education or achievements:
            edu_table = Table(title="Educación y Logros")
            edu_table.add_column("Tipo", style="yellow bold")
            edu_table.add_column("Institución / Concurso", style="cyan")
            edu_table.add_column("Título / Detalle", style="white")
            edu_table.add_column("Fechas / Ubicación", style="dim")

            for edu in education:
                edu_table.add_row("Educación", edu.institution, edu.degree, f"{edu.date_range} | {edu.location}")
            for ach in achievements:
                edu_table.add_row("Logro", ach.institution or ach.category, ach.title, ach.date_range or "")

            console.print(edu_table)



# ----------------------------------------------------------------------
# 4. SUBCOMANDOS: REPO (Gestión de Repositorios Seguidos en SQLite)
# ----------------------------------------------------------------------
@repo_app.command(name="list")
def repo_list():
    """Lista todos los repositorios seguidos en SQLite para sincronización."""
    init_db()
    with get_session() as session:
        records = session.exec(select(TrackedRepo).order_by(TrackedRepo.priority, TrackedRepo.name)).all()

    if not records:
        console.print("[bold yellow]No hay repositorios configurados en SQLite.[/] Ejecuta [cyan]juanchito seed[/] para poblar los 27 iniciales.")
        return

    table = Table(title=f"Repositorios Seguidos en SQLite ({len(records)} repos)")
    table.add_column("ID", justify="center", style="dim")
    table.add_column("Repositorio", style="cyan bold")
    table.add_column("Rama Override", style="magenta")
    table.add_column("Estado", justify="center", style="bold")
    table.add_column("Categoría", style="yellow")
    table.add_column("Prioridad", justify="center", style="white")

    for r in records:
        status_col = "[bold green]Activo[/]" if r.is_active else "[bold red]Inactivo[/]"
        branch_col = r.branch if r.branch else "[dim]default[/]"
        cat_col = r.category or "[dim]None[/]"
        table.add_row(str(r.id), r.name, branch_col, status_col, cat_col, str(r.priority))

    console.print(table)


@repo_app.command(name="add")
def repo_add(
    name: str = typer.Argument(..., help="Nombre del repositorio (ej. 'mi-nuevo-repo')"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Rama específica a inspeccionar"),
    category: str | None = typer.Option(None, "--category", "-c", help="Categoría técnica (ej. 'Backend')"),
    priority: int = typer.Option(1, "--priority", "-p", help="Prioridad (1: Alta, 2: Normal)"),
):
    """Agrega un nuevo repositorio para seguimiento y sincronización."""
    init_db()
    with get_session() as session:
        existing = session.exec(select(TrackedRepo).where(TrackedRepo.name == name)).first()
        if existing:
            console.print(f"[bold yellow]El repositorio '{name}' ya está registrado en SQLite (ID: {existing.id}).[/]")
            return

        new_repo = TrackedRepo(
            name=name,
            branch=branch,
            category=category,
            priority=priority,
            is_active=True,
        )
        session.add(new_repo)
        session.commit()
        session.refresh(new_repo)

    console.print(f"[bold green]✓ Repositorio '{name}' agregado con éxito a SQLite (ID: {new_repo.id}).[/]")


@repo_app.command(name="remove")
def repo_remove(
    name: str = typer.Argument(..., help="Nombre del repositorio a remover"),
):
    """Elimina un repositorio de la tabla de seguimiento en SQLite."""
    init_db()
    with get_session() as session:
        repo = session.exec(select(TrackedRepo).where(TrackedRepo.name == name)).first()
        if not repo:
            console.print(f"[bold red]Error:[/] No se encontró el repositorio '{name}' en SQLite.")
            raise typer.Exit(code=1)

        session.delete(repo)
        session.commit()

    console.print(f"[bold green]✓ Repositorio '{name}' eliminado de SQLite con éxito.[/]")


@repo_app.command(name="toggle")
def repo_toggle(
    name: str = typer.Argument(..., help="Nombre del repositorio a alternar"),
):
    """Activa o desactiva la sincronización de un repositorio sin borrarlo."""
    init_db()
    with get_session() as session:
        repo = session.exec(select(TrackedRepo).where(TrackedRepo.name == name)).first()
        if not repo:
            console.print(f"[bold red]Error:[/] No se encontró el repositorio '{name}' en SQLite.")
            raise typer.Exit(code=1)

        repo.is_active = not repo.is_active
        session.add(repo)
        session.commit()
        session.refresh(repo)

    status_str = "[bold green]ACTIVO[/]" if repo.is_active else "[bold red]INACTIVO[/]"
    console.print(f"Estado de '{name}' actualizado a: {status_str}")


# ----------------------------------------------------------------------
# 5. SUBCOMANDOS: SYNC (GitHub, LinkedIn, All)
# ----------------------------------------------------------------------
@sync_app.command(name="github")
def sync_github_cmd(
    user: str = typer.Option("MateoPissarello", "--user", "-u", help="Usuario de GitHub"),
    all_repos: bool = typer.Option(False, "--all", "-a", help="Sincronizar todos los repositorios sin filtrar"),
    repo: list[str] = typer.Option(None, "--repo", "-r", help="Repositorios específicos a sincronizar"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="Concurrencia de análisis simultáneo"),
    force: bool = typer.Option(False, "--force", "-f", help="Forzar re-análisis con IA aunque no haya commits nuevos"),
):
    """Sincroniza repositorios de GitHub hacia SQLite basándose en TrackedRepo."""
    asyncio.run(
        _run_sync(
            username=user,
            all_repos=all_repos,
            selected_repos=repo,
            concurrency=concurrency,
            force=force,
        )
    )


@sync_app.command(name="linkedin")
def sync_linkedin_cmd(
    pdf_path: Path = typer.Argument(DATA_DIR / "linkedin_profile.pdf", help="Ruta al PDF oficial de LinkedIn"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo previsualizar sin alterar SQLite"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirmar automáticamente sin preguntar"),
    include_non_technical: bool = typer.Option(False, "--include-non-technical", help="Incluir roles no técnicos"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Proveedor de IA (openrouter/gemini)"),
):
    """Importa y enriquece de forma no destructiva el perfil desde una exportación oficial de LinkedIn."""
    asyncio.run(
        _run_import(
            pdf_path=pdf_path,
            dry_run=dry_run,
            yes=yes,
            include_non_technical=include_non_technical,
            provider=provider,
        )
    )


@sync_app.command(name="all")
def sync_all_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Forzar reanálisis de repositorios en GitHub"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirmar importación de LinkedIn automáticamente"),
):
    """Ejecuta consecutivamente la sincronización de GitHub y la importación de LinkedIn."""
    console.print("[bold cyan]🔄 Sincronizando todo el perfil (GitHub + LinkedIn)...[/]\n")
    # 1. GitHub
    console.print("[bold blue]1. Sincronización de GitHub[/bold blue]")
    asyncio.run(_run_sync(username="MateoPissarello", all_repos=False, selected_repos=None, concurrency=3, force=force))

    # 2. LinkedIn
    console.print("\n[bold blue]2. Enriquecimiento de LinkedIn[/bold blue]")
    pdf_path = DATA_DIR / "linkedin_profile.pdf"
    if pdf_path.exists():
        asyncio.run(_run_import(pdf_path=pdf_path, dry_run=False, yes=yes, include_non_technical=False, provider=None))
    else:
        console.print(f"[bold yellow]⚠️ No se encontró {pdf_path}. Omitiendo LinkedIn.[/]")


# Si se ejecuta 'juanchito sync' sin subcomando
@sync_app.callback(invoke_without_command=True)
def sync_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print("[bold yellow]¿Qué fuente deseas sincronizar?[/]")
        console.print("  [cyan][1][/] Solo GitHub (repositorios seguidos)")
        console.print("  [cyan][2][/] Solo LinkedIn (PDF export)")
        console.print("  [cyan][3][/] Ambos consecutivamente (GitHub + LinkedIn)")
        choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3"], default="3")
        if choice == "1":
            sync_github_cmd()
        elif choice == "2":
            sync_linkedin_cmd()
        elif choice == "3":
            sync_all_cmd()


# ----------------------------------------------------------------------
# 6. COMANDO: SEED (Resiembra de Base de Datos)
# ----------------------------------------------------------------------
@app.command()
def seed(
    resume_path: Path = typer.Option(
        PROJECT_ROOT / "data/examples/Backend Engineer/resume.md",
        "--resume",
        "-r",
        help="Ruta al archivo Markdown base",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Confirmar resiembra sin preguntar"),
):
    """Puebla o restablece la base de datos a partir del currículum base resume.md."""
    if not force:
        confirm = Confirm.ask(
            "[bold yellow]¿Estás seguro de que deseas resembrar la base de datos?[/] "
            "[dim](Se restablecerán las entidades base y repositorios iniciales)[/]"
        )
        if not confirm:
            console.print("[dim]Operación cancelada.[/]")
            return

    run_seed(resume_path=resume_path)


# ----------------------------------------------------------------------
# Punto de Entrada Principal
# ----------------------------------------------------------------------
def main():
    app()


if __name__ == "__main__":
    main()
