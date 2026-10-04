import asyncio

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
    if selected_repos:
        targets = selected_repos
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


    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Analizando e ingestando repositorios...", total=None)
        results = await service.sync_all(
            username=username,
            max_concurrency=concurrency,
            repo_names=targets,
            force=force,
        )
        progress.update(task, completed=100, total=100)

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
    user: str = typer.Option("MateoPissarello", "--user", "-u", help="Usuario de GitHub"),
    all_repos: bool = typer.Option(False, "--all", "-a", help="Sincronizar todos los repositorios"),
    repo: list[str] = typer.Option(None, "--repo", "-r", help="Repositorios específicos a sincronizar"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="Concurrencia de análisis simultáneo"),
    force: bool = typer.Option(False, "--force", "-f", help="Forzar re-análisis con IA aunque no haya commits nuevos"),
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

