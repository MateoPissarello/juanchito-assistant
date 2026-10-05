import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from juanchito_assitant.db.database import init_db
from juanchito_assitant.ingest.github_ingest import GitHubIngestService

app = typer.Typer(help="Sincronizador inteligente de repositorios de GitHub con OpenRouter / Qwen")
console = Console()


async def _run_sync(
    username: str,
    all_repos: bool,
    selected_repos: list[str] | None,
    concurrency: int,
    force: bool,
):
    init_db()
    service = GitHubIngestService()

    targets = None
    if isinstance(selected_repos, (list, tuple, set)) and len(selected_repos) > 0:
        targets = list(selected_repos)
        console.print(f"[bold cyan]🎯 Sincronizando {len(targets)} repositorios específicos:[/] {', '.join(targets)}")
    elif all_repos:
        console.print(
            "[bold yellow]🌐 Sincronizando TODOS los repositorios públicos y privados (excluyendo forks)...[/]"
        )
    else:
        # Cargar dinámicamente desde la tabla TrackedRepo en SQLite
        targets = service.get_active_tracked_names()
        if not targets:
            console.print("[bold yellow]⚠️ No hay repositorios en la tabla 'trackedrepo'. Sincronizando repositorios públicos...[/]")
        else:
            console.print(f"[bold cyan]⭐ Sincronizando lista de repositorios seguidos en SQLite ({len(targets)} repos).[/]")
        console.print("[dim]Tip: Usa '--all' para sincronizar todos o '-r <nombre>' para uno específico.[/]")
        if force:
            console.print("[bold red]⚡ Modo --force activo: Se re-analizarán todos los repositorios con IA.[/]\n")
        else:
            console.print("[dim]ℹ️ Detección inteligente activa: Se omitirán repositorios sin nuevos commits.[/]\n")


    def _handle_status(repo_name: str, status: str, message: str):
        if status == "skipped":
            console.print(f"  [dim]⏩ {repo_name}:[/dim] [dim]{message}[/dim]")
        elif status == "analyzing":
            console.print(f"  [bold yellow]🤖 {repo_name}:[/bold yellow] [cyan]{message}[/cyan]")
        elif status == "completed":
            console.print(f"  [bold green]✓ {repo_name}:[/bold green] [green]{message}[/green]")
        elif status == "not_found":
            console.print(f"  [bold red]⚠️ {repo_name}:[/bold red] [red]{message}[/red]")
        elif status == "error":
            console.print(f"  [bold red]✗ {repo_name}:[/bold red] [red]{message}[/red]")

    console.print("[dim]Iniciando escaneo e ingesta concurrente...[/dim]\n")
    results = await service.sync_all(
        username=username,
        max_concurrency=concurrency,
        repo_names=targets,
        force=force,
        on_status=_handle_status,
    )

    analyzed_count = sum(1 for _, was_updated in results if was_updated)
    skipped_count = len(results) - analyzed_count

    console.print(
        f"\n[bold green]✅ Sincronización finalizada con éxito![/] "
        f"({analyzed_count} analizados con IA, {skipped_count} sin cambios detectados)\n"
    )

    # Mostrar tabla resumen con Rich
    table = Table(title="Proyectos Personales Sincronizados (profile.db)")
    table.add_column("Proyecto", style="cyan bold", no_wrap=True)
    table.add_column("Branch", style="magenta")
    table.add_column("Estado Sync", style="bold")
    table.add_column("README", style="white")
    table.add_column("Tecnologías", style="green")
    table.add_column("Viñetas de Impacto (Google XYZ)", style="dim")

    for p, was_updated in results:
        status_col = "[bold green]🔄 Analizado[/]" if was_updated else "[dim]⏩ Sin cambios[/]"
        readme_status = "[bold green]✅ Adecuado[/]" if p.has_readme else "[bold yellow]📝 Sugerido[/]"
        tech_list = ", ".join(p.technologies[:4]) if p.technologies else "None"
        first_bullet = p.bullets[0][:90] + "..." if p.bullets else "None"
        table.add_row(
            p.name,
            p.branch,
            status_col,
            readme_status,
            tech_list,
            first_bullet,
        )

    console.print(table)


@app.command()
def main(
    user: Annotated[str, typer.Option("--user", "-u", help="Usuario de GitHub")] = "MateoPissarello",
    all_repos: Annotated[bool, typer.Option("--all", "-a", help="Sincronizar todos los repositorios")] = False,
    repo: Annotated[list[str] | None, typer.Option("--repo", "-r", help="Repositorios específicos a sincronizar")] = None,
    concurrency: Annotated[int, typer.Option("--concurrency", "-c", help="Concurrencia de análisis simultáneo")] = 3,
    force: Annotated[bool, typer.Option("--force", "-f", help="Forzar re-análisis con IA aunque no haya commits nuevos")] = False,
):
    """Punto de entrada para ejecutar la sincronización de repositorios."""
    asyncio.run(
        _run_sync(
            username=user,
            all_repos=all_repos,
            selected_repos=repo,
            concurrency=concurrency,
            force=force,
        )
    )


if __name__ == "__main__":
    app()

