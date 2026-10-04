from pathlib import Path
from rich.console import Console
from rich.table import Table
from juanchito_assitant.config import DB_PATH, PROJECT_ROOT
from juanchito_assitant.db.database import init_db, get_session
from juanchito_assitant.ingest.markdown_parser import parse_resume_markdown, seed_database_from_profile

console = Console()

def run_seed(
    resume_path: Path = PROJECT_ROOT / "data/examples/Backend Engineer/resume.md",
    db_path: Path = DB_PATH
) -> None:
    """Lee el archivo resume.md y puebla la base de datos SQLite."""
    console.print(f"[bold cyan]🌱 Iniciando siembra de perfil desde:[/] [yellow]{resume_path}[/]")
    
    if not resume_path.exists():
        console.print(f"[bold red]❌ Error:[/] No se encontró el archivo en {resume_path}")
        return

    init_db(db_path=db_path)
    content = resume_path.read_text(encoding="utf-8")
    profile = parse_resume_markdown(content)

    with get_session(db_path=db_path) as session:
        seed_database_from_profile(profile, session)

    console.print("[bold green]✅ Siembra completada exitosamente en la base de datos.[/]\n")
    
    # Mostrar resumen en terminal con Rich
    table = Table(title="Resumen del Perfil Sembrado")
    table.add_column("Entidad", style="cyan")
    table.add_column("Cantidad", style="magenta")
    table.add_column("Detalles", style="white")

    table.add_row("Personal Info", "1", f"{profile.personal.full_name} ({profile.personal.headline})")
    
    total_initiatives = sum(len(e.projects) for e in profile.experiences)
    comp_names = ", ".join(e.company for e in profile.experiences)
    table.add_row("Experiencias Laborales", str(len(profile.experiences)), comp_names)
    table.add_row("Iniciativas Técnicas", str(total_initiatives), "AICodeFixer, AIForms, Zammad, RAG...")
    table.add_row("Certificaciones", str(len(profile.certifications)), "AWS (4), Cisco, Oracle, HackerRank, UNAL")
    table.add_row("Educación", str(len(profile.education)), profile.education[0].institution if profile.education else "")
    table.add_row("Categorías de Skills", str(len(profile.skills)), ", ".join(s.category for s in profile.skills[:4]) + "...")
    table.add_row("Logros Adicionales", str(len(profile.additional_achievements)), profile.additional_achievements[0].title if profile.additional_achievements else "")

    console.print(table)

if __name__ == "__main__":
    run_seed()
