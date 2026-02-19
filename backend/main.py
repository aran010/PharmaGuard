"""
PharmaGuard Backend — FastAPI Application
Pharmacogenomics analysis API.
# Reload trigger: Migrated to Groq API.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from vcf_parser import parse_vcf_content, group_variants_by_gene, infer_diplotype
from risk_engine import assess_risk, GENE_DRUG_MAP, SUPPORTED_DRUGS
from groq_integration import generate_clinical_explanation

load_dotenv()

app = FastAPI(
    title="PharmaGuard API",
    description="Pharmacogenomics analysis API — VCF parsing, risk assessment, and AI-powered clinical explanations",
    version="1.0.0",
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "PharmaGuard API",
        "version": "1.0.0",
        "llm_provider": "Groq Cloud API"
    }


@app.get("/api/supported-drugs")
async def get_supported_drugs():
    """Return the list of supported drugs."""
    return {
        "drugs": SUPPORTED_DRUGS,
        "gene_drug_map": GENE_DRUG_MAP,
    }


@app.post("/api/parse-vcf")
async def parse_vcf(file: UploadFile = File(...)):
    """
    Parse a VCF file and extract pharmacogenomic variants.
    Returns structured variant list per gene.
    """
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    result = parse_vcf_content(text)
    grouped = group_variants_by_gene(result["variants"])

    # Infer diplotypes
    diplotypes = {}
    for gene, variants in grouped.items():
        dip = infer_diplotype(variants)
        if dip:
            diplotypes[gene] = dip

    return {
        **result,
        "grouped_by_gene": grouped,
        "inferred_diplotypes": diplotypes,
    }


@app.post("/api/assess-risk")
async def assess_risk_endpoint(
    gene: str = Form(...),
    diplotype: str = Form(...),
    drug: str = Form(...),
):
    """
    Assess drug risk for a given gene, diplotype, and drug.
    """
    result = assess_risk(gene, diplotype, drug)
    return result


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    drug: str = Form(...),
):
    """
    Master analysis endpoint.
    Takes a VCF file + drug name → returns complete pharmacogenomic analysis with AI explanation.
    """
    # 1. Parse VCF

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    parse_result = parse_vcf_content(text)
    grouped = group_variants_by_gene(parse_result["variants"])

    # 2. Find relevant gene for this drug
    drug_upper = drug.upper()
    primary_gene = GENE_DRUG_MAP.get(drug_upper, None)

    if not primary_gene:
        raise HTTPException(
            status_code=400,
            detail=f"Drug '{drug}' is not in supported list. Supported: {', '.join(SUPPORTED_DRUGS)}"
        )

    # 3. Get variants for the primary gene
    gene_variants = grouped.get(primary_gene, [])

    if not gene_variants:
        # No variants found for this gene
        return _build_response(
            drug=drug_upper,
            primary_gene=primary_gene,
            diplotype="Unknown",
            phenotype="Unknown",
            risk_data={
                "risk_label": "Unknown",
                "severity": "unknown",
                "confidence_score": 0.50,
                "action": f"No {primary_gene} variants detected in VCF",
                "dosing_adjustment": "Cannot assess — insufficient genetic data",
                "monitoring": "Consider ordering targeted pharmacogenomic test",
            },
            variants=gene_variants,
            parse_result=parse_result,
            llm_explanation=None,
        )

    # 4. Infer diplotype
    diplotype = infer_diplotype(gene_variants)
    if not diplotype:
        diplotype = "Unknown"

    # 5. Risk assessment
    risk_data = assess_risk(primary_gene, diplotype, drug_upper)
    phenotype = risk_data.get("phenotype", "Unknown")

    # 6. Claude AI explanation
    llm_explanation = generate_clinical_explanation(
        gene=primary_gene,
        diplotype=diplotype,
        phenotype=phenotype,
        drug=drug_upper,
        risk_label=risk_data["risk_label"],
        variants=gene_variants,
    )

    # 7. Assemble full response
    return _build_response(
        drug=drug_upper,
        primary_gene=primary_gene,
        diplotype=diplotype,
        phenotype=phenotype,
        risk_data=risk_data,
        variants=gene_variants,
        parse_result=parse_result,
        llm_explanation=llm_explanation,
    )


def _build_response(
    drug: str,
    primary_gene: str,
    diplotype: str,
    phenotype: str,
    risk_data: dict,
    variants: list,
    parse_result: dict,
    llm_explanation: Optional[dict],
) -> dict:
    """Build the full JSON response schema."""
    patient_id = f"PATIENT_{uuid.uuid4().hex[:6].upper()}"

    return {
        "patient_id": patient_id,
        "drug": drug,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "risk_assessment": {
            "risk_label": risk_data.get("risk_label", "Unknown"),
            "confidence_score": risk_data.get("confidence_score", 0.50),
            "severity": risk_data.get("severity", "unknown"),
        },
        "pharmacogenomic_profile": {
            "primary_gene": primary_gene,
            "diplotype": diplotype,
            "phenotype": phenotype,
            "detected_variants": [
                {"rsid": v["rsid"], "gene": v["gene"], "star": v["star"]}
                for v in variants
            ],
        },
        "clinical_recommendation": {
            "action": risk_data.get("action", "Consult specialist"),
            "dosing_adjustment": risk_data.get("dosing_adjustment", "N/A"),
            "monitoring": risk_data.get("monitoring", "Standard monitoring"),
        },
        "llm_generated_explanation": llm_explanation or {},
        "quality_metrics": {
            "vcf_parsing_success": len(parse_result.get("parsing_errors", [])) == 0,
            "variants_detected": parse_result.get("total_variants", 0),
            "genes_analyzed": len(parse_result.get("genes_found", [])),
        },
    }


# Serving Frontend Static Files
# In production (Docker), static files are built into the 'static' directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    # SPA Fallback: Serve index.html for any unknown routes
    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        return FileResponse(os.path.join(static_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
