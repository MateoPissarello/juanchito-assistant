import pytest
from sqlmodel import Session, SQLModel, create_engine

from juanchito_assitant.agents.matcher import (
    MatcherAgent,
    extract_key_terms,
    matches_term,
)
from juanchito_assitant.models.job import JobRequirements
from juanchito_assitant.models.profile import (
    PersonalInfo,
    PersonalProject,
    SkillCategory,
    TrackedRepo,
    WorkExperience,
    WorkProject,
)


def get_mock_profile_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    # 1. Personal Info
    session.add(PersonalInfo(full_name="Mateo Pissarello", github="MateoPissarello", location="Bogotá, Colombia"))

    # 2. Blend360 Colombia
    exp_blend = WorkExperience(company="Blend360 Colombia", role="Trainee", start_date="Nov. 2024", end_date="Jan. 2026", location="Bogotá", order_index=1)
    session.add(exp_blend)
    session.flush()

    # AICodeFixer
    session.add(WorkProject(
        work_experience_id=exp_blend.id,
        name="AICodeFixer",
        bullets=[
            "Created **AICodeFixer**, an automated tool leveraging **Generative AI** and **ClaudeCode**.",
            "Built serverless workflows using **FastAPI**, **AWS Lambda**, and **DynamoDB**.",
        ],
        technologies=["FastAPI", "Generative AI", "ClaudeCode", "AWS Lambda", "DynamoDB", "Python"],
    ))
    # AIForms
    session.add(WorkProject(
        work_experience_id=exp_blend.id,
        name="AIForms",
        bullets=[
            "Developed dynamic form generator using **Docassemble** and deployed on **AWS Fargate**.",
            "Implemented **Infrastructure as Code** with **AWS CDK (TypeScript)**.",
        ],
        technologies=["AWS Fargate", "AWS CDK", "TypeScript", "Docassemble"],
    ))
    # Zammad on Kubernetes
    session.add(WorkProject(
        work_experience_id=exp_blend.id,
        name="Zammad on Kubernetes (EKS)",
        bullets=[
            "Architected highly available deployment on **Amazon EKS** using **AWS CDK**.",
            "Implemented continuous deployment with **ArgoCD** and monitoring with **Grafana**.",
        ],
        technologies=["Amazon EKS", "AWS CDK", "Kubernetes", "ArgoCD", "Grafana"],
    ))
    # RAG Cali City Hall
    session.add(WorkProject(
        work_experience_id=exp_blend.id,
        name="RAG – Hacienda A Un Click Project (Cali City Hall)",
        bullets=[
            "Implemented a **Retrieval-Augmented Generation (RAG)** architecture for document queries.",
            "Deployed solution on **Amazon Bedrock** integrating **S3 Vector Store** for semantic search.",
        ],
        technologies=["Retrieval-Augmented Generation (RAG)", "Amazon Bedrock", "S3 Vector Store", "Python"],
    ))

    # 3. PhenoScience
    exp_pheno = WorkExperience(company="PhenoScience", role="Backend Developer", start_date="Sep. 2023", end_date="Sep. 2024", location="Remote", order_index=2)
    session.add(exp_pheno)
    session.flush()

    session.add(WorkProject(
        work_experience_id=exp_pheno.id,
        name="PhenoScience Backend",
        bullets=[
            "Migrated backend from Django to **FastAPI** with **PostgreSQL**.",
            "Implemented real-time chat with **WebSockets** and an **OpenAI API** chatbot.",
        ],
        technologies=["FastAPI", "PostgreSQL", "WebSockets", "OpenAI", "Python"],
    ))

    # 4. Icebergdata
    exp_ice = WorkExperience(company="Icebergdata", role="Junior Backend Engineer", start_date="Jan. 2026", end_date="Mar. 2026", location="Bogotá", order_index=3)
    session.add(exp_ice)
    session.flush()

    session.add(WorkProject(
        work_experience_id=exp_ice.id,
        name="Icebergdata Core",
        bullets=[
            "Developed web scraping microservices in Python with proxy rotation.",
            "Implemented data extraction pipelines with Playwright.",
        ],
        technologies=["Python", "Playwright", "Web Scraping"],
    ))

    # 5. Tracked Repos & Personal Projects
    session.add(TrackedRepo(name="juanchito-assistant", category="AI / Multi-Agent Systems", is_active=True))
    session.add(PersonalProject(
        name="juanchito-assistant",
        description="Automated assistant that generates tailored CVs using multi-agent systems, LLMs, and FastAPI.",
        bullets=["Multi-agent orchestration system with LLM agents and SSE streaming."],
        technologies=["Python", "FastAPI", "LLM", "Multi-Agent", "OpenRouter", "Google Gemini"],
    ))

    session.add(TrackedRepo(name="goofish-scraping", category="Web Scraping / Backend", is_active=True))
    session.add(PersonalProject(
        name="goofish-scraping",
        description="Scalable web scraping microservices with proxy rotation.",
        bullets=["Automated scraping pipelines."],
        technologies=["Python", "Playwright", "FastAPI"],
    ))

    session.add(SkillCategory(category="Data & AI", skills=["LLMs", "RAG", "OpenAI", "Generative AI"]))
    session.add(SkillCategory(category="Backend", skills=["Python", "FastAPI", "PostgreSQL"]))

    session.commit()
    return session


def test_extract_key_terms_atomic_breakdown():
    raw_reqs = [
        "Production AWS experience",
        "Infrastructure as Code (CDK, CloudFormation, or Terraform)",
        "Experience with retrieval systems (RAG), embedding pipelines, or hybrid search (vector + keyword)",
        "Strong software fundamentals: OOP, design patterns, SOLID principles",
        "Design and consumption of well-designed HTTP APIs (REST, GraphQL, or similar)",
    ]
    terms = extract_key_terms(raw_reqs)
    # Validate essential tokens are extracted
    assert "CDK" in terms or "cdk" in terms
    assert "Terraform" in terms or "terraform" in terms
    assert "RAG" in terms or "rag" in terms
    assert "OOP" in terms or "oop" in terms
    assert "REST" in terms or "rest" in terms
    assert "GraphQL" in terms or "graphql" in terms
    assert "infrastructure as code" in terms
    # Ensure long multi-sentence fillers were stripped
    assert not any("experience with retrieval systems" in t for t in terms)


def test_word_boundary_matching():
    # "rag" should NOT match "storage" or "fragment"
    techs_set = {"python", "fastapi", "s3 storage"}
    corpus_clean = "deployed microservices with s3 storage and fragmented data"
    assert not matches_term("rag", corpus_clean, techs_set)

    # "rag" SHOULD match "RAG", "RAG solution", or "Retrieval-Augmented Generation"
    corpus_rag = "implemented a high performance rag pipeline for search"
    assert matches_term("rag", corpus_rag, techs_set)

    corpus_synonym = "deployed retrieval-augmented generation on bedrock"
    assert matches_term("rag", corpus_synonym, techs_set)


def test_ai_job_matching_prioritizes_rag_and_juanchito():
    session = get_mock_profile_session()
    matcher = MatcherAgent(session)

    caseware_job = JobRequirements(
        job_title="Artificial Intelligence Software Developer",
        company_name="Caseware",
        seniority_level="Mid-Senior",
        must_have_skills=[
            "Production AWS experience",
            "Infrastructure as Code (CDK, CloudFormation, or Terraform)",
            "Agent frameworks",
            "Orchestration of tool-using AI systems",
            "Design and consumption of well-designed HTTP APIs (REST, GraphQL, or similar)",
        ],
        nice_to_have_skills=[
            "Experience with retrieval systems (RAG), embedding pipelines, or hybrid search (vector + keyword)",
            "LLMOps experience",
        ],
        core_responsibilities=["Build agentic AI systems and LLM services"],
        ats_keywords=["LLM services", "Multi-agent orchestration", "Retrieval pipelines"],
        role_summary="The Artificial Intelligence Software Developer will build agentic AI systems and RAG pipelines.",
    )

    ctx = matcher.match(caseware_job)

    # 1. Personal Projects: juanchito-assistant MUST be selected
    assert len(ctx.github_matches) >= 1
    assert ctx.github_matches[0].name == "juanchito-assistant"
    assert ctx.github_matches[0].match_score > 10.0

    # 2. Work Projects: BOTH AICodeFixer and RAG Cali MUST be selected under Blend360!
    selected_names = [w.project_name for w in ctx.work_matches]
    assert "AICodeFixer" in selected_names
    assert "RAG – Hacienda A Un Click Project (Cali City Hall)" in selected_names

    # 3. AIForms should NOT displace RAG for an AI role
    assert "AIForms" not in selected_names


def test_devops_job_prioritizes_eks_and_iac():
    session = get_mock_profile_session()
    matcher = MatcherAgent(session)

    devops_job = JobRequirements(
        job_title="Cloud & DevOps Platform Engineer",
        must_have_skills=["Kubernetes", "AWS CDK", "ArgoCD", "Infrastructure as Code"],
        nice_to_have_skills=["Grafana", "Docker"],
        core_responsibilities=["Manage EKS clusters"],
        ats_keywords=["Kubernetes", "CI/CD"],
        role_summary="Manage cloud platform infrastructure on AWS EKS.",
    )

    ctx = matcher.match(devops_job)
    selected_names = [w.project_name for w in ctx.work_matches]

    # Zammad on Kubernetes (EKS) and AIForms (IaC/CDK) should be top
    assert "Zammad on Kubernetes (EKS)" in selected_names
    assert "AIForms" in selected_names
