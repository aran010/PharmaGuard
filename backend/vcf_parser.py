"""
VCF Parser Module
Extracts pharmacogenomic variants from VCF files.
Targets 6 key genes: CYP2D6, CYP2C19, CYP2C9, SLCO1B1, TPMT, DPYD

Supports ALL VCF formats (v3.x, v4.x, etc.) and real-world VCF files
that don't have custom GENE/STAR/RS INFO tags — uses rsID lookup.
"""

from typing import Optional
import re

TARGET_GENES = {"CYP2D6", "CYP2C19", "CYP2C9", "SLCO1B1", "TPMT", "DPYD"}


# ─── rsID → Gene/Star allele lookup table ────────────────────────────────────
# This allows parsing real-world VCF files that don't have custom INFO tags.
# Based on PharmVar / dbSNP / CPIC variant-star allele mappings.
RSID_LOOKUP = {
    # CYP2D6 variants
    "rs3892097":  {"gene": "CYP2D6",  "star": "*4"},    # CYP2D6*4 — splicing defect
    "rs1065852":  {"gene": "CYP2D6",  "star": "*4"},    # CYP2D6*4 — 100C>T
    "rs5030655":  {"gene": "CYP2D6",  "star": "*6"},    # CYP2D6*6 — frameshift
    "rs16947":    {"gene": "CYP2D6",  "star": "*2"},    # CYP2D6*2 — R296C
    "rs1135840":  {"gene": "CYP2D6",  "star": "*2"},    # CYP2D6*2 — S486T
    "rs28371706": {"gene": "CYP2D6",  "star": "*17"},   # CYP2D6*17
    "rs28371725": {"gene": "CYP2D6",  "star": "*41"},   # CYP2D6*41 — reduced function
    "rs35742686": {"gene": "CYP2D6",  "star": "*3"},    # CYP2D6*3 — frameshift
    "rs5030867":  {"gene": "CYP2D6",  "star": "*7"},    # CYP2D6*7
    "rs5030865":  {"gene": "CYP2D6",  "star": "*8"},    # CYP2D6*8
    "rs1080985":  {"gene": "CYP2D6",  "star": "*2"},    # CYP2D6*2 upstream variant
    "rs28371703": {"gene": "CYP2D6",  "star": "*15"},   # CYP2D6*15
    "rs769258":   {"gene": "CYP2D6",  "star": "*5"},    # CYP2D6*5

    # CYP2C19 variants
    "rs4244285":  {"gene": "CYP2C19", "star": "*2"},    # CYP2C19*2 — splicing defect
    "rs4986893":  {"gene": "CYP2C19", "star": "*3"},    # CYP2C19*3 — premature stop
    "rs12248560": {"gene": "CYP2C19", "star": "*17"},   # CYP2C19*17 — ultra-rapid
    "rs28399504": {"gene": "CYP2C19", "star": "*4"},    # CYP2C19*4
    "rs56337013": {"gene": "CYP2C19", "star": "*5"},    # CYP2C19*5
    "rs72552267": {"gene": "CYP2C19", "star": "*6"},    # CYP2C19*6
    "rs72558186": {"gene": "CYP2C19", "star": "*7"},    # CYP2C19*7
    "rs41291556": {"gene": "CYP2C19", "star": "*8"},    # CYP2C19*8

    # CYP2C9 variants
    "rs1799853":  {"gene": "CYP2C9",  "star": "*2"},    # CYP2C9*2 — R144C
    "rs1057910":  {"gene": "CYP2C9",  "star": "*3"},    # CYP2C9*3 — I359L
    "rs28371686": {"gene": "CYP2C9",  "star": "*5"},    # CYP2C9*5
    "rs9332131":  {"gene": "CYP2C9",  "star": "*6"},    # CYP2C9*6
    "rs28371685": {"gene": "CYP2C9",  "star": "*11"},   # CYP2C9*11

    # SLCO1B1 variants
    "rs4149056":  {"gene": "SLCO1B1", "star": "*5"},    # SLCO1B1*5 — V174A
    "rs2306283":  {"gene": "SLCO1B1", "star": "*1b"},   # SLCO1B1*1b — N130D
    "rs4149015":  {"gene": "SLCO1B1", "star": "*15"},   # SLCO1B1*15
    "rs11045819": {"gene": "SLCO1B1", "star": "*1b"},   # SLCO1B1 P155T

    # TPMT variants
    "rs1800462":  {"gene": "TPMT",    "star": "*2"},    # TPMT*2 — A80P
    "rs1800460":  {"gene": "TPMT",    "star": "*3A"},   # TPMT*3A — A154T
    "rs1142345":  {"gene": "TPMT",    "star": "*3A"},   # TPMT*3A — Y240C
    "rs1800584":  {"gene": "TPMT",    "star": "*3B"},   # TPMT*3B
    "rs1800584":  {"gene": "TPMT",    "star": "*3C"},   # TPMT*3C — Y240C only

    # DPYD variants
    "rs3918290":  {"gene": "DPYD",    "star": "*2A"},   # DPYD*2A — IVS14+1G>A (critical)
    "rs55886062": {"gene": "DPYD",    "star": "*13"},   # DPYD*13 — I560S
    "rs67376798": {"gene": "DPYD",    "star": "*HapB3"},# DPYD HapB3 — D949V
    "rs75017182": {"gene": "DPYD",    "star": "*HapB3"},# DPYD HapB3 upstream
    "rs56038477": {"gene": "DPYD",    "star": "*HapB3"},# DPYD HapB3 intronic
}

# ─── Known pharmacogenomic positions (chrom:pos → gene) ─────────────────────
# Fallback if rsID is unknown but position matches a pharma gene region
POSITION_GENE_MAP = {
    # CYP2D6 on chr22 (GRCh37: ~42,522,000-42,527,000 / GRCh38: ~42,126,000-42,131,000)
    ("chr22", 42522000, 42528000): "CYP2D6",
    ("22", 42522000, 42528000): "CYP2D6",
    ("chr22", 42126000, 42132000): "CYP2D6",
    ("22", 42126000, 42132000): "CYP2D6",

    # CYP2C19 on chr10 (GRCh37: ~96,520,000-96,613,000 / GRCh38: ~94,762,000-94,855,000)
    ("chr10", 96520000, 96614000): "CYP2C19",
    ("10", 96520000, 96614000): "CYP2C19",
    ("chr10", 94762000, 94856000): "CYP2C19",
    ("10", 94762000, 94856000): "CYP2C19",

    # CYP2C9 on chr10 (GRCh37: ~96,698,000-96,750,000 / GRCh38: ~94,938,000-94,990,000)
    ("chr10", 96698000, 96751000): "CYP2C9",
    ("10", 96698000, 96751000): "CYP2C9",
    ("chr10", 94938000, 94991000): "CYP2C9",
    ("10", 94938000, 94991000): "CYP2C9",

    # SLCO1B1 on chr12 (GRCh37: ~21,283,000-21,393,000)
    ("chr12", 21283000, 21394000): "SLCO1B1",
    ("12", 21283000, 21394000): "SLCO1B1",

    # TPMT on chr6 (GRCh37: ~18,128,000-18,155,000)
    ("chr6", 18128000, 18156000): "TPMT",
    ("6", 18128000, 18156000): "TPMT",

    # DPYD on chr1 (GRCh37: ~97,543,000-97,921,000)
    ("chr1", 97543000, 97922000): "DPYD",
    ("1", 97543000, 97922000): "DPYD",
}


def parse_info_field(info: str) -> dict:
    """Parse VCF INFO field into key-value pairs.
    Example: GENE=CYP2D6;STAR=*4;RS=rs3892097 → {GENE: CYP2D6, STAR: *4, RS: rs3892097}
    Handles standard VCF INFO fields too (AC=1;AF=0.5;AN=2;DP=30 etc.)
    """
    result = {}
    if info == "." or not info:
        return result
    for item in info.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
        else:
            # Flag fields (no value)
            result[item.strip()] = True
    return result


def lookup_by_rsid(rsid: str) -> Optional[dict]:
    """Look up gene and star allele from rsID."""
    return RSID_LOOKUP.get(rsid, None)


def lookup_by_position(chrom: str, pos: int) -> Optional[str]:
    """Look up gene by genomic position (fallback)."""
    for (c, start, end), gene in POSITION_GENE_MAP.items():
        if chrom == c and start <= pos <= end:
            return gene
    return None


def parse_vcf_content(content: str) -> dict:
    """
    Parse VCF file content and extract pharmacogenomic variants.
    Works with ALL VCF versions and real-world files.

    Strategy:
    1. If custom GENE/STAR/RS INFO tags exist → use them directly
    2. Else, look up rsID in our pharmacogenomic database
    3. Else, check if the genomic position falls within a known pharma gene region

    Returns:
        {
            "variants": [...],
            "genes_found": ["CYP2D6", "CYP2C19"],
            "total_variants": 3,
            "total_lines_processed": 100,
            "vcf_version": "VCFv4.2",
            "parsing_errors": []
        }
    """
    variants = []
    genes_found = set()
    parsing_errors = []
    total_lines = 0
    vcf_version = "Unknown"

    lines = content.strip().split("\n")

    for line_num, line in enumerate(lines, 1):
        # Extract VCF version from header
        if line.startswith("##fileformat="):
            vcf_version = line.split("=", 1)[1].strip()
            continue

        # Skip headers and comments
        if line.startswith("#"):
            continue

        line = line.strip()
        if not line:
            continue

        total_lines += 1
        parts = line.split("\t")
        if len(parts) < 8:
            # Try splitting by multiple spaces/whitespace
            parts = re.split(r"\s+", line)

        if len(parts) < 5:
            # Minimum VCF: CHROM POS ID REF ALT
            parsing_errors.append(
                f"Line {line_num}: insufficient columns ({len(parts)} found, minimum 5 expected)"
            )
            continue

        chrom = parts[0]
        pos_str = parts[1]
        rsid = parts[2] if len(parts) > 2 else "."
        ref = parts[3] if len(parts) > 3 else "."
        alt = parts[4] if len(parts) > 4 else "."
        info = parts[7] if len(parts) > 7 else ""

        try:
            pos_int = int(pos_str)
        except ValueError:
            parsing_errors.append(f"Line {line_num}: invalid position '{pos_str}'")
            continue

        info_dict = parse_info_field(info)

        gene = None
        star = ""
        variant_rsid = rsid

        # ── Strategy 1: Custom INFO tags ──
        if "GENE" in info_dict:
            gene = info_dict["GENE"].upper()
            star = info_dict.get("STAR", "")
            variant_rsid = info_dict.get("RS", rsid)

        # ── Strategy 2: rsID lookup ──
        if gene is None and rsid != "." and rsid.startswith("rs"):
            lookup = lookup_by_rsid(rsid)
            if lookup:
                gene = lookup["gene"]
                star = lookup["star"]
                variant_rsid = rsid

        # ── Strategy 3: Position-based lookup (fallback) ──
        if gene is None:
            pos_gene = lookup_by_position(chrom, pos_int)
            if pos_gene:
                gene = pos_gene
                variant_rsid = rsid if rsid != "." else f"pos_{chrom}_{pos_int}"

        # Skip if not a pharmacogenomic variant
        if gene is None or gene not in TARGET_GENES:
            continue

        genes_found.add(gene)

        variants.append({
            "rsid": variant_rsid,
            "gene": gene,
            "star": star,
            "chrom": chrom,
            "pos": pos_int,
            "ref": ref,
            "alt": alt,
        })

    return {
        "variants": variants,
        "genes_found": sorted(list(genes_found)),
        "total_variants": len(variants),
        "total_lines_processed": total_lines,
        "vcf_version": vcf_version,
        "parsing_errors": parsing_errors,
    }


def group_variants_by_gene(variants: list) -> dict:
    """Group variants by gene for downstream analysis."""
    grouped = {}
    for v in variants:
        gene = v["gene"]
        if gene not in grouped:
            grouped[gene] = []
        grouped[gene].append(v)
    return grouped


def infer_diplotype(gene_variants: list) -> Optional[str]:
    """
    Infer diplotype from a list of variants for a single gene.
    Uses star alleles found in the variants. If two distinct star alleles are found,
    returns them as a diplotype. If only one is found, duplicates it (homozygous assumption).
    """
    stars = []
    for v in gene_variants:
        star = v.get("star", "")
        if star and star not in stars:
            stars.append(star)

    if len(stars) == 0:
        return None
    elif len(stars) == 1:
        # If multiple variants with the same star allele → homozygous
        if len(gene_variants) >= 2:
            return f"{stars[0]}/{stars[0]}"
        else:
            return f"{stars[0]}/*1"  # Assume *1 (normal) for other allele
    else:
        return f"{stars[0]}/{stars[1]}"
