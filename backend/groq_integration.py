"""
Groq AI Integration Module
Uses Groq via OpenAI-compatible API to generate clinical pharmacogenomics explanations.
"""

import os
import json
from openai import OpenAI


def get_client() -> OpenAI:
    """Get OpenAI client configured for Groq with API key from environment."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Fallback to checking other keys
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("XAI_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def generate_clinical_explanation(
    gene: str,
    diplotype: str,
    phenotype: str,
    drug: str,
    risk_label: str,
    variants: list,
) -> dict:
    """
    Generate a clinical explanation using Groq (Llama 3).
    """
    variants_str = ", ".join(
        [f"{v.get('rsid', 'N/A')} ({v.get('gene', '')}, {v.get('star', '')})" for v in variants]
    )

    prompt = f"""You are a clinical pharmacogenomics expert. Given the following patient data, generate a structured clinical explanation.

Patient Genetic Data:
- Gene: {gene}
- Diplotype: {diplotype}
- Phenotype: {phenotype}
- Drug: {drug}
- Risk Level: {risk_label}
- Detected Variants: {variants_str}

Generate a response in this EXACT JSON format:
{{
  "summary": "2-3 sentence plain English summary of why this patient has this risk",
  "biological_mechanism": "explain how the variant affects drug metabolism at molecular level",
  "clinical_significance": "what happens clinically if this drug is given as-is",
  "cpic_guideline_reference": "cite the relevant CPIC guideline",
  "alternative_recommendations": ["list", "of", "safer", "alternatives"]
}}

Be specific. Cite the rsID variants. Use clinical terminology but stay accessible."""

    try:
        client = get_client()
        # Using Llama 3.3 70b which is fast and very capable
        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful clinical pharmacogenomics expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            # Ensure JSON mode if supported or just prompt for it
            response_format={"type": "json_object"}
        )

        response_text = message.choices[0].message.content

        # Extract JSON from the response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback extraction logic
            json_match = response_text
            if "```json" in response_text:
                json_match = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_match = response_text.split("```")[1].split("```")[0]
            elif "{" in response_text:
                start = response_text.index("{")
                end = response_text.rindex("}") + 1
                json_match = response_text[start:end]

            return json.loads(json_match)

    except Exception as e:
        # Log the error for debugging in deployment environments
        print(f"ERROR: Groq API Explanation failed: {str(e)}")
        
        # Return a fallback explanation if API fails
        return {
            "summary": f"Patient carries {diplotype} diplotype in {gene}, classified as {phenotype}. "
                       f"This results in a '{risk_label}' risk for {drug}.",
            "biological_mechanism": f"The {gene} gene variants affect the enzyme responsible for "
                                    f"metabolizing {drug}. The {diplotype} diplotype alters enzyme activity.",
            "clinical_significance": f"Risk level is '{risk_label}'. Clinical guidance should be followed.",
            "cpic_guideline_reference": f"Refer to CPIC guidelines for {gene}-{drug} interaction.",
            "alternative_recommendations": ["Consult a clinical pharmacist for alternatives"],
            "_error": str(e),
            "_note": "This is a fallback explanation. Groq API was unavailable."
        }
