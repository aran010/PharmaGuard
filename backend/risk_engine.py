"""
Risk Engine Module
CPIC-guideline-based rule engine for pharmacogenomic risk assessment.
Maps gene diplotypes → phenotypes → drug risk predictions.
"""

# ─── Diplotype → Phenotype mapping ───────────────────────────────────────────────

PHENOTYPE_MAP = {
    "CYP2D6": {
        "*1/*1": "NM",    # Normal Metabolizer
        "*1/*2": "RM",    # Rapid Metabolizer
        "*2/*2": "URM",   # Ultra-Rapid Metabolizer
        "*1/*4": "IM",    # Intermediate Metabolizer
        "*4/*4": "PM",    # Poor Metabolizer
        "*4/*1": "IM",
        "*1/*3": "IM",
        "*3/*4": "PM",
        "*1/*5": "IM",
        "*5/*5": "PM",
        "*1/*6": "IM",
    },
    "CYP2C19": {
        "*1/*1": "NM",
        "*1/*2": "IM",
        "*2/*2": "PM",
        "*1/*3": "IM",
        "*2/*3": "PM",
        "*3/*3": "PM",
        "*1/*17": "RM",
        "*17/*17": "URM",
    },
    "CYP2C9": {
        "*1/*1": "NM",
        "*1/*2": "IM",
        "*1/*3": "IM",
        "*2/*2": "PM",
        "*2/*3": "IM",
        "*3/*3": "PM",
    },
    "SLCO1B1": {
        "*1/*1": "NF",   # Normal Function
        "*1/*5": "DF",   # Decreased Function
        "*5/*5": "PF",   # Poor Function
        "*1/*15": "DF",
        "*15/*15": "PF",
    },
    "TPMT": {
        "*1/*1": "NM",
        "*1/*3A": "IM",
        "*3A/*3A": "PM",
        "*1/*3C": "IM",
        "*3C/*3C": "PM",
        "*1/*2": "IM",
    },
    "DPYD": {
        "*1/*1": "NM",
        "*1/*2A": "IM",
        "*2A/*2A": "PM",
        "*1/*13": "IM",
        "*2A/*1": "IM",
    },
}


# ─── Drug Risk Lookup Table (CPIC Guidelines) ───────────────────────────────────

RISK_TABLE = {
    # CYP2D6 ↔ Drug interactions
    ("CYP2D6", "PM", "CODEINE"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.92,
        "action": "Avoid Codeine",
        "dosing_adjustment": "N/A — contraindicated",
        "monitoring": "Switch to non-opioid analgesic (e.g., acetaminophen, NSAIDs)",
    },
    ("CYP2D6", "NM", "CODEINE"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.92,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required",
        "monitoring": "Standard monitoring",
    },
    ("CYP2D6", "IM", "CODEINE"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.85,
        "action": "Reduce dose or use alternative",
        "dosing_adjustment": "Reduce dose by 25-50%",
        "monitoring": "Monitor for reduced efficacy",
    },
    ("CYP2D6", "RM", "CODEINE"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.90,
        "action": "Avoid Codeine — ultra-rapid metabolism",
        "dosing_adjustment": "N/A — contraindicated due to rapid conversion to morphine",
        "monitoring": "Switch to non-opioid analgesic",
    },
    ("CYP2D6", "URM", "CODEINE"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.92,
        "action": "Avoid Codeine — ultra-rapid metabolism",
        "dosing_adjustment": "N/A — contraindicated due to rapid conversion to morphine",
        "monitoring": "Switch to non-opioid analgesic",
    },

    # CYP2C19 ↔ Clopidogrel
    ("CYP2C19", "PM", "CLOPIDOGREL"): {
        "risk_label": "Ineffective",
        "severity": "high",
        "confidence_score": 0.92,
        "action": "Use alternative antiplatelet",
        "dosing_adjustment": "Switch to prasugrel or ticagrelor",
        "monitoring": "Monitor platelet function",
    },
    ("CYP2C19", "NM", "CLOPIDOGREL"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.92,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required",
        "monitoring": "Standard monitoring",
    },
    ("CYP2C19", "IM", "CLOPIDOGREL"): {
        "risk_label": "Adjust Dosage",
        "severity": "moderate",
        "confidence_score": 0.85,
        "action": "Consider alternative antiplatelet",
        "dosing_adjustment": "Consider increased dose or alternative",
        "monitoring": "Monitor platelet function closely",
    },
    ("CYP2C19", "RM", "CLOPIDOGREL"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.88,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required",
        "monitoring": "Standard monitoring",
    },
    ("CYP2C19", "URM", "CLOPIDOGREL"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.85,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required — may have enhanced response",
        "monitoring": "Monitor for bleeding",
    },

    # CYP2C9 ↔ Warfarin
    ("CYP2C9", "IM", "WARFARIN"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "confidence_score": 0.90,
        "action": "Reduce warfarin dose",
        "dosing_adjustment": "Reduce initial dose by 25-50%",
        "monitoring": "Frequent INR monitoring; target INR 2.0-3.0",
    },
    ("CYP2C9", "PM", "WARFARIN"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.92,
        "action": "Significantly reduce warfarin dose",
        "dosing_adjustment": "Reduce initial dose by 50-80%",
        "monitoring": "Very frequent INR monitoring; high bleeding risk",
    },
    ("CYP2C9", "NM", "WARFARIN"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.92,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required",
        "monitoring": "Standard INR monitoring",
    },

    # SLCO1B1 ↔ Simvastatin
    ("SLCO1B1", "PF", "SIMVASTATIN"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.92,
        "action": "Avoid simvastatin or use lowest dose",
        "dosing_adjustment": "Use alternative statin (rosuvastatin or pravastatin)",
        "monitoring": "Monitor for myopathy, check CK levels",
    },
    ("SLCO1B1", "DF", "SIMVASTATIN"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "confidence_score": 0.88,
        "action": "Limit simvastatin dose",
        "dosing_adjustment": "Do not exceed 20mg daily",
        "monitoring": "Monitor for muscle pain and CK levels",
    },
    ("SLCO1B1", "NF", "SIMVASTATIN"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.92,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required",
        "monitoring": "Standard monitoring",
    },

    # TPMT ↔ Azathioprine
    ("TPMT", "PM", "AZATHIOPRINE"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.92,
        "action": "Avoid azathioprine or drastically reduce dose",
        "dosing_adjustment": "Reduce dose to 10% of standard, or use alternative",
        "monitoring": "Frequent CBC monitoring; high risk of myelosuppression",
    },
    ("TPMT", "IM", "AZATHIOPRINE"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "confidence_score": 0.88,
        "action": "Reduce azathioprine dose",
        "dosing_adjustment": "Start at 50% of standard dose",
        "monitoring": "Regular CBC monitoring",
    },
    ("TPMT", "NM", "AZATHIOPRINE"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.92,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required",
        "monitoring": "Standard monitoring",
    },

    # DPYD ↔ Fluorouracil
    ("DPYD", "PM", "FLUOROURACIL"): {
        "risk_label": "Toxic",
        "severity": "critical",
        "confidence_score": 0.92,
        "action": "Avoid fluorouracil",
        "dosing_adjustment": "N/A — contraindicated",
        "monitoring": "Use alternative chemotherapy regimen",
    },
    ("DPYD", "IM", "FLUOROURACIL"): {
        "risk_label": "Adjust Dosage",
        "severity": "high",
        "confidence_score": 0.88,
        "action": "Reduce fluorouracil dose",
        "dosing_adjustment": "Reduce dose by 50%",
        "monitoring": "Close monitoring for toxicity (mucositis, myelosuppression)",
    },
    ("DPYD", "NM", "FLUOROURACIL"): {
        "risk_label": "Safe",
        "severity": "low",
        "confidence_score": 0.92,
        "action": "Use standard dosing",
        "dosing_adjustment": "None required",
        "monitoring": "Standard monitoring",
    },
}


# ─── Gene → Drug mapping (which gene is relevant for which drug) ─────────────────

GENE_DRUG_MAP = {
    "CODEINE": "CYP2D6",
    "TRAMADOL": "CYP2D6",
    "CLOPIDOGREL": "CYP2C19",
    "WARFARIN": "CYP2C9",
    "SIMVASTATIN": "SLCO1B1",
    "AZATHIOPRINE": "TPMT",
    "FLUOROURACIL": "DPYD",
    "5-FU": "DPYD",
}

SUPPORTED_DRUGS = list(GENE_DRUG_MAP.keys())


def get_phenotype(gene: str, diplotype: str) -> str:
    """Look up phenotype from gene + diplotype."""
    gene_map = PHENOTYPE_MAP.get(gene, {})
    phenotype = gene_map.get(diplotype, None)

    # Try reversed diplotype
    if phenotype is None and "/" in diplotype:
        parts = diplotype.split("/")
        reversed_dip = f"{parts[1]}/{parts[0]}"
        phenotype = gene_map.get(reversed_dip, None)

    return phenotype if phenotype else "Unknown"


def assess_risk(gene: str, diplotype: str, drug: str) -> dict:
    """
    Assess drug risk for a given gene, diplotype, and drug.

    Returns:
        {
            "risk_label": "Toxic" | "Safe" | "Adjust Dosage" | "Ineffective" | "Unknown",
            "severity": "critical" | "high" | "moderate" | "low" | "unknown",
            "confidence_score": 0.0-1.0,
            "phenotype": "PM" | "IM" | "NM" | "RM" | "URM" | "Unknown",
            "action": str,
            "dosing_adjustment": str,
            "monitoring": str,
        }
    """
    drug_upper = drug.upper()
    gene_upper = gene.upper()

    phenotype = get_phenotype(gene_upper, diplotype)

    # Look up risk
    risk_key = (gene_upper, phenotype, drug_upper)
    risk_data = RISK_TABLE.get(risk_key, None)

    if risk_data:
        return {
            **risk_data,
            "phenotype": phenotype,
            "gene": gene_upper,
            "diplotype": diplotype,
            "drug": drug_upper,
        }

    # Default for unknown combinations
    return {
        "risk_label": "Unknown",
        "severity": "unknown",
        "confidence_score": 0.50,
        "phenotype": phenotype,
        "gene": gene_upper,
        "diplotype": diplotype,
        "drug": drug_upper,
        "action": "Consult clinical pharmacogenomics specialist",
        "dosing_adjustment": "No guideline available for this combination",
        "monitoring": "Standard monitoring recommended",
    }
