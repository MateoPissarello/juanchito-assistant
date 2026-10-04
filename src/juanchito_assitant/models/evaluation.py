from pydantic import BaseModel, Field

class ScoreBreakdown(BaseModel):
    ats_keyword_match: int = Field(..., ge=0, le=25, description="Coincidencia de términos clave técnicos y habilidades (0-25)")
    role_relevance: int = Field(..., ge=0, le=25, description="Alineación y relevancia de los proyectos/experiencias seleccionados (0-25)")
    quantifiable_impact: int = Field(..., ge=0, le=20, description="Uso de fórmula Google XYZ y métricas cuantificables en viñetas (0-20)")
    factual_integrity: int = Field(..., ge=0, le=15, description="Veracidad frente al Master Profile sin alucinaciones (0-15)")
    format_and_length: int = Field(..., ge=0, le=15, description="Cumplimiento de sintaxis resume.lol, secciones y longitud (0-15)")

class EvaluationResult(BaseModel):
    total_score: int = Field(..., ge=0, le=100)
    meets_threshold: bool
    breakdown: ScoreBreakdown
    strengths: list[str] = Field(default_factory=list)
    critical_weaknesses: list[str] = Field(default_factory=list)
    actionable_improvements: list[str] = Field(default_factory=list)

class IterationRecord(BaseModel):
    iteration: int
    generated_markdown: str
    evaluation: EvaluationResult
