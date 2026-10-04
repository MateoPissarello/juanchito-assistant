from pydantic import BaseModel, Field


class LinkedInExperienceItem(BaseModel):
    """Experiencia laboral individual extraída de LinkedIn."""

    company: str = Field(description="Nombre normalizado de la empresa o cliente.")
    role: str = Field(description="Cargo o título del puesto.")
    location: str | None = Field(default=None, description="Ubicación (ej. 'Bogotá, Colombia', 'Remote').")
    start_date: str = Field(description="Fecha de inicio normalizada (ej. 'Jan. 2026' o 'Nov. 2024').")
    end_date: str = Field(default="Present", description="Fecha de fin normalizada (ej. 'Mar. 2026' o 'Present').")
    is_current: bool = Field(default=False, description="True si actualmente desempeña el rol.")
    is_technical: bool = Field(
        default=True,
        description="True si el rol es técnico (software, backend, cloud, data, IA). False si es soporte telefónico, ventas, etc.",
    )
    summary: str | None = Field(default=None, description="Breve descripción general del rol.")
    bullets: list[str] = Field(
        default_factory=list,
        description="Viñetas o responsabilidades destacadas con métricas e impacto en inglés o formato Google XYZ.",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Tecnologías, frameworks y herramientas detectadas (ej. Python, FastAPI, Docker, AWS).",
    )


class LinkedInCertificationItem(BaseModel):
    """Certificación o licencia extraída de LinkedIn."""

    issuer: str | None = Field(default=None, description="Institución emisora (ej. 'Amazon Web Services (AWS)', 'Cisco', 'Oracle').")
    title: str = Field(description="Nombre completo oficial de la certificación.")
    issue_date: str | None = Field(default=None, description="Fecha de emisión o vigencia si está disponible.")


class LinkedInEducationItem(BaseModel):
    """Educación formal o diplomados extraídos de LinkedIn."""

    institution: str = Field(description="Institución académica (ej. 'Universidad Sergio Arboleda').")
    degree: str = Field(description="Título o carrera (ej. 'B.Sc. in Computer Science & Artificial Intelligence').")
    date_range: str | None = Field(default=None, description="Rango de fechas (ej. 'Jul. 2022 - Nov. 2027').")
    location: str | None = Field(default=None, description="Ubicación.")


class LinkedInProfileExtract(BaseModel):
    """Extracción semántica completa del perfil de LinkedIn."""

    full_name: str = Field(description="Nombre completo del titular.")
    headline: str | None = Field(default=None, description="Titular profesional.")
    location: str | None = Field(default=None, description="Ubicación general.")
    summary: str | None = Field(default=None, description="Extracto o 'About' profesional.")
    experiences: list[LinkedInExperienceItem] = Field(default_factory=list)
    certifications: list[LinkedInCertificationItem] = Field(default_factory=list)
    education: list[LinkedInEducationItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list, description="Lista de aptitudes y skills detectadas.")
    languages: list[str] = Field(
        default_factory=list, description="Idiomas con su nivel (ej. ['Español (Native)', 'Inglés (Bilingual)']).")


class LinkedInEnrichmentSummary(BaseModel):
    """Resumen de los cambios y enriquecimientos aplicados o detectados."""

    added_experiences: list[str] = Field(default_factory=list)
    existing_experiences: list[str] = Field(default_factory=list)
    skipped_experiences: list[str] = Field(default_factory=list)
    added_certifications: list[str] = Field(default_factory=list)
    added_education: list[str] = Field(default_factory=list)
    added_skills: list[str] = Field(default_factory=list)
    updated_fields: list[str] = Field(default_factory=list)

