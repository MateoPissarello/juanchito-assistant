from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel


class PersonalInfo(SQLModel, table=True):
    """Información de contacto y variables de cabecera de resume.lol."""

    id: int | None = Field(default=1, primary_key=True)
    full_name: str = "Mateo Pissarello"
    timezone: str = "GMT-05"
    location: str = "Bogotá, Colombia"
    email: str = "@EMAIL"
    phone: str = "@PHONE"
    linkedin: str = "mateo-pissarello"
    github: str = "MateoPissarello"
    headline: str = "Backend Engineer | AWS | Distributed Systems"
    profile_summary: str = (
        "Backend Engineer with a background in Computer Science and Artificial Intelligence, "
        "experienced in backend development, cloud computing, and AI-driven solutions. "
        "Specialized in AWS architectures, distributed systems, and applied machine learning. "
        "Proven track record of leading and delivering production-grade solutions that improve "
        "operational efficiency, scalability, and decision-making."
    )
    # Variables adicionales de resume.lol (e.g. {"@REDACTED": "false", "@MARATON": "Programming Contest"})
    extra_variables: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))


class WorkExperience(SQLModel, table=True):
    """Cargos y empresas donde has trabajado."""

    id: int | None = Field(default=None, primary_key=True)
    role: str  # Ej: "Trainee", "Backend Developer"
    company: str = Field(index=True)  # Ej: "Blend360 Colombia", "PhenoScience"
    location: str  # Ej: "Bogotá, Colombia (On-site)", "Remote"
    start_date: str  # Ej: "Nov. 2024"
    end_date: str = "Present"  # Ej: "Jan. 2026"
    is_current: bool = False
    order_index: int = 0

    # Relación 1 a N con las iniciativas / proyectos desarrollados en esta empresa
    projects: list["WorkProject"] = Relationship(back_populates="work_experience", cascade_delete=True)


class WorkProject(SQLModel, table=True):
    """Iniciativas o proyectos técnicos desarrollados dentro de un trabajo."""

    id: int | None = Field(default=None, primary_key=True)
    work_experience_id: int = Field(foreign_key="workexperience.id", nullable=False)
    name: str = Field(index=True)  # Ej: "AICodeFixer", "AIForms", "Zammad on Kubernetes (EKS)"

    # Viñetas de impacto cuantificable (fórmula Google XYZ) y tecnologías asociadas
    bullets: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    technologies: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    priority_weight: int = 1

    # Relación con la empresa
    work_experience: WorkExperience | None = Relationship(back_populates="projects")


class PersonalProject(SQLModel, table=True):
    """Proyectos personales o de código abierto (GitHub u otros)."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # Ej: "CanvaToPdf", "goofish-scraping", "ParcialCV3Final"
    repo_url: str | None = None
    branch: str = "main"
    description: str | None = None
    bullets: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    technologies: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    has_readme: bool = True
    suggested_readme: str | None = None


class Certification(SQLModel, table=True):
    """Cursos y certificaciones profesionales."""

    id: int | None = Field(default=None, primary_key=True)
    issuer: str = Field(index=True)  # Ej: "Amazon Web Services (AWS)", "Cisco", "Oracle"
    title: str  # Ej: "AWS Certified Solutions Architect - Associate"
    issue_date: str  # Ej: "Apr. 2025"


class Education(SQLModel, table=True):
    """Educación formal universitaria."""

    id: int | None = Field(default=None, primary_key=True)
    institution: str  # Ej: "Universidad Sergio Arboleda"
    degree: str  # Ej: "B.Sc. in Computer Science & Artificial Intelligence"
    date_range: str  # Ej: "Jul. 2022 – Present"
    location: str = "Bogotá, Colombia"


class SkillCategory(SQLModel, table=True):
    """Habilidades técnicas agrupadas por categoría."""

    id: int | None = Field(default=None, primary_key=True)
    category: str = Field(unique=True, index=True)  # Ej: "Languages", "Backend", "Cloud & DevOps"
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class AdditionalAchievement(SQLModel, table=True):
    """Logros adicionales, maratones de programación, premios o voluntariado."""

    id: int | None = Field(default=None, primary_key=True)
    category: str = "Programming Contest"  # "Programming Contest", "Hackathon", "Award", "Volunteer"
    title: str  # Ej: "Programming Contest"
    institution: str | None = "Universidad Sergio Arboleda"
    location: str | None = "Bogotá, Colombia"
    date_range: str | None = "Nov. 2024"
    description_bullets: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    links: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))


class FullProfile(SQLModel):
    """Vista agregada en memoria de todo el perfil para los agentes."""

    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    experiences: list[WorkExperience] = Field(default_factory=list)
    personal_projects: list[PersonalProject] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[SkillCategory] = Field(default_factory=list)
    additional_achievements: list[AdditionalAchievement] = Field(default_factory=list)
