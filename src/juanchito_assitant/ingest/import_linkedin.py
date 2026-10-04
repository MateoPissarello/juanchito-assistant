import asyncio
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
import typer

from juanchito_assitant.agents.linkedin_parser import LinkedInParserAgent
from juanchito_assitant.config import DATA_DIR
from juanchito_assitant.db.database import get_session, init_db
from juanchito_assitant.ingest.linkedin_enricher import enrich_profile_from_linkedin
from juanchito_assitant.ingest.pdf_extractor import extract_text_from_pdf

app = typer.Typer(help="Importador y enriquecedor de perfil desde exportaciones oficiales de LinkedIn en PDF.")
console = Console()


async def _run_import(
    pdf_path: Path,
    dry_run: bool,
    yes: bool,
    include_non_technical: bool,
    provider: str | None,
):
    init_db()

    console.print(
        Panel.fit(
            f"[bold blue]LinkedIn Profile Importer[/bold blue]\n"
            f"[dim]Archivo:[/dim] [cyan]{pdf_path}[/cyan]\n"
            f"[dim]Modo no destructivo:[/dim] [green]Activo[/green]",
            border_style="blue",
        )
    )

    if not pdf_path.exists():
        console.print(f"[bold red]Error:[/bold red] No se encontró el archivo: {pdf_path}")
        raise typer.Exit(code=1)

    # 1. Extracción de texto plano
    with console.status("[bold cyan]Extrayendo texto del PDF con pypdf...[/bold cyan]"):
        try:
            raw_text = extract_text_from_pdf(pdf_path)
        except Exception as exc:
            console.print(f"[bold red]Error al extraer texto:[/bold red] {exc}")
            raise typer.Exit(code=1)

    console.print(f"  [green]✓[/green] Texto extraído con éxito ({len(raw_text)} caracteres)")

    # 2. Análisis y estructuración con LLM
    parser = LinkedInParserAgent(provider=provider)
    with console.status(f"[bold cyan]Analizando texto con LLM ({parser.provider.upper()} - {parser.model})...[/bold cyan]"):
        try:
            extract = await parser.parse(raw_text)
        except Exception as exc:
            console.print(f"[bold red]Error en el análisis LLM:[/bold red] {exc}")
            raise typer.Exit(code=1)

    console.print(f"  [green]✓[/green] Perfil parseado: [bold]{extract.full_name}[/bold]")
    if extract.headline:
        console.print(f"    [dim]Titular:[/dim] {extract.headline}")

    # 3. Calcular Diff con profile.db en dry_run
    with get_session() as session:
        summary_dry = enrich_profile_from_linkedin(
            session=session,
            extract=extract,
            dry_run=True,
            include_non_technical=include_non_technical,
        )

    # 4. Mostrar tabla de cambios detectados
    table = Table(title="Resumen de Enriquecimiento Detectado", border_style="cyan")
    table.add_column("Categoría", style="bold", width=22)
    table.add_column("Estado / Acción", style="green", width=18)
    table.add_column("Detalle", style="white")

    for item in summary_dry.added_experiences:
        table.add_row("Experiencia", "[bold green]+ NUEVA[/bold green]", item)

    for item in summary_dry.existing_experiences:
        table.add_row("Experiencia", "[dim cyan]= PRESERVADA[/dim cyan]", item)

    for item in summary_dry.skipped_experiences:
        table.add_row("Experiencia", "[dim yellow]- OMITIDA[/dim yellow]", item)

    for item in summary_dry.added_certifications:
        table.add_row("Certificación", "[bold green]+ NUEVA[/bold green]", item)

    for item in summary_dry.added_skills:
        table.add_row("Habilidad (Skill)", "[bold green]+ NUEVA[/bold green]", item)

    for item in summary_dry.added_education:
        table.add_row("Educación", "[bold green]+ NUEVA[/bold green]", item)

    console.print()
    console.print(table)
    console.print()

    has_changes = bool(
        summary_dry.added_experiences
        or summary_dry.added_certifications
        or summary_dry.added_skills
        or summary_dry.added_education
    )

    if not has_changes:
        console.print("[bold yellow]No se detectaron nuevas entidades para agregar.[/bold yellow] El perfil ya está sincronizado.")
        return

    if dry_run:
        console.print("[dim yellow]Modo --dry-run activo. No se realizaron cambios en la base de datos.[/dim yellow]")
        return

    # 5. Confirmación del usuario
    should_apply = yes or Confirm.ask("[bold green]¿Deseas aplicar estos enriquecimientos a profile.db?[/bold green]")
    if not should_apply:
        console.print("[yellow]Operación cancelada. profile.db permanece intacta.[/yellow]")
        return

    # 6. Aplicar cambios reales
    with get_session() as session:
        real_summary = enrich_profile_from_linkedin(
            session=session,
            extract=extract,
            dry_run=False,
            include_non_technical=include_non_technical,
        )

    console.print()
    console.print(
        Panel(
            f"[bold green]¡Perfil enriquecido con éxito en SQLite![/bold green]\n\n"
            f"• [bold]{len(real_summary.added_experiences)}[/bold] nuevas empresas / iniciativas técnicas agregadas.\n"
            f"• [bold]{len(real_summary.added_certifications)}[/bold] nuevas certificaciones añadidas.\n"
            f"• [bold]{len(real_summary.added_skills)}[/bold] nuevas habilidades categorizadas.",
            border_style="green",
        )
    )


@app.command()
def main(
    pdf_path: Path = typer.Argument(
        DATA_DIR / "linkedin_profile.pdf",
        help="Ruta al archivo PDF exportado desde LinkedIn.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Previsualiza los cambios sin persistir en profile.db.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Aplica los cambios automáticamente sin pedir confirmación interactiva.",
    ),
    include_non_technical: bool = typer.Option(
        False,
        "--include-non-technical",
        help="Incluye roles no técnicos (ej. atención al cliente).",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Proveedor de LLM ('openrouter' o 'gemini').",
    ),
):
    """Importa y enriquece tu base de datos profile.db a partir de un PDF de LinkedIn."""
    asyncio.run(
        _run_import(
            pdf_path=pdf_path,
            dry_run=dry_run,
            yes=yes,
            include_non_technical=include_non_technical,
            provider=provider,
        )
    )


if __name__ == "__main__":
    app()
