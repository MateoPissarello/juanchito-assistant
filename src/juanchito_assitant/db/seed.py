from pathlib import Path

from rich.console import Console
from rich.table import Table

from sqlmodel import Session, select

from juanchito_assitant.config import DB_PATH, PROJECT_ROOT
from juanchito_assitant.db.database import get_session, init_db
from juanchito_assitant.ingest.markdown_parser import parse_resume_markdown, seed_database_from_profile
from juanchito_assitant.models.profile import TrackedRepo

console = Console()

INITIAL_TRACKED_REPOS: list[dict] = [
    {"name": "goofish-scraping", "branch": "scraping-v2", "category": "Web Scraping / Backend", "priority": 1},
    {"name": "CanvaToPdf", "branch": "main", "category": "Backend / Automation", "priority": 1},
    {"name": "GradeClassifier", "branch": "main", "category": "AI / ML", "priority": 1},
    {"name": "ParcialCV3Final", "branch": "master", "category": "Computer Vision", "priority": 1},
    {"name": "ApiLungCancerChatbot", "branch": "main", "category": "NLP / Healthcare", "priority": 1},
    {"name": "AutomataVisualizer", "branch": "main", "category": "Algorithms", "priority": 1},
    {"name": "arquitectura-serverless-lab", "branch": "main", "category": "Cloud / AWS", "priority": 1},
    {"name": "basic-crud-fastapi", "branch": "main", "category": "Backend / FastAPI", "priority": 1},
    {"name": "miwa-backend", "branch": "main", "category": "Backend", "priority": 2},
    {"name": "miwa-frontend", "branch": "main", "category": "Frontend", "priority": 2},
    {"name": "DCGan", "branch": "main", "category": "Deep Learning", "priority": 2},
    {"name": "descentralized-pc-terraform", "branch": "main", "category": "DevOps / Terraform", "priority": 2},
    {"name": "SkynetAdhoc", "branch": "main", "category": "Distributed Systems", "priority": 2},
    {"name": "cine_colombia", "branch": "main", "category": "Backend", "priority": 2},
    {"name": "restaurant_booking", "branch": "main", "category": "Backend", "priority": 2},
    {"name": "torres-hanoi-distributed", "branch": "main", "category": "Distributed Systems", "priority": 2},
    {"name": "Buffalo", "branch": "main", "category": "Backend", "priority": 2},
    {"name": "concurrency-so", "branch": "main", "category": "Operating Systems", "priority": 2},
    {"name": "parser-tree", "branch": "main", "category": "Compilers", "priority": 2},
    {"name": "birds-data-filter", "branch": "main", "category": "Data Engineering", "priority": 2},
    {"name": "lineal-regression-ecoli", "branch": "main", "category": "Data Science", "priority": 2},
    {"name": "NS3-simulations", "branch": "main", "category": "Networking", "priority": 2},
    {"name": "CalculatorANTLR", "branch": "main", "category": "Compilers", "priority": 2},
    {"name": "simulacion-tx-rx", "branch": "main", "category": "Telecommunications", "priority": 2},
    {"name": "AFD", "branch": "main", "category": "Theory of Computation", "priority": 2},
    {"name": "vacuum-threejs", "branch": "main", "category": "Simulation", "priority": 2},
    {"name": "parcial-algoritmochat-node-aws", "branch": "main", "category": "Cloud / Node.js", "priority": 2},
]


def seed_tracked_repos(session: Session) -> int:
    """Inserta repositorios curados iniciales en la tabla SQLite trackedrepo si no existen."""
    added = 0
    for item in INITIAL_TRACKED_REPOS:
        existing = session.exec(select(TrackedRepo).where(TrackedRepo.name == item["name"])).first()
        if not existing:
            repo = TrackedRepo(
                name=item["name"],
                branch=item.get("branch"),
                category=item.get("category"),
                priority=item.get("priority", 1),
                is_active=True,
            )
            session.add(repo)
            added += 1
    session.commit()
    return added


def run_seed(
    resume_path: Path = PROJECT_ROOT / "data/examples/Backend Engineer/resume.md", db_path: Path = DB_PATH
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
        tracked_added = seed_tracked_repos(session)
        total_tracked = len(session.exec(select(TrackedRepo)).all())

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
    table.add_row(
        "Educación", str(len(profile.education)), profile.education[0].institution if profile.education else ""
    )
    table.add_row(
        "Categorías de Skills", str(len(profile.skills)), ", ".join(s.category for s in profile.skills[:4]) + "..."
    )
    table.add_row(
        "Logros Adicionales",
        str(len(profile.additional_achievements)),
        profile.additional_achievements[0].title if profile.additional_achievements else "",
    )
    table.add_row(
        "Repositorios Seguidos",
        str(total_tracked),
        f"{tracked_added} nuevos sembrados en trackedrepo",
    )

    console.print(table)


if __name__ == "__main__":
    run_seed()

