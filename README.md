# PharmaGuard 🧬

**AI-Powered Pharmacogenomics Analysis Platform**

Upload a VCF file (genetic data) + select a drug → PharmaGuard analyzes genetic variants → predicts risk (Safe / Adjust Dosage / Toxic / Ineffective) → Claude AI generates a clinical explanation → outputs structured JSON.

## Tech Stack

- **Frontend:** React (Vite) 
- **Backend:** Python FastAPI
- **AI:** Groq API (`llama-3.3-70b-versatile`) for LLM explanations
- **Deploy:** Vercel (frontend) + Render (backend)

## Quick Start

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your Groq API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run
python main.py
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Sample VCF Files

Test files are in `sample_data/`:
- `sample_test.vcf` — CYP2D6 *4/*4 PM → Codeine = Toxic
- `sample_warfarin.vcf` — CYP2C9 *2/*3 IM → Warfarin = Adjust Dosage
- `sample_multi.vcf` — Multiple genes for comprehensive testing

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/parse-vcf` | POST | Parse VCF file, extract variants |
| `/api/assess-risk` | POST | Gene + diplotype + drug → risk |
| `/api/analyze` | POST | Master: VCF + drug → full JSON |
| `/api/supported-drugs` | GET | List supported drugs |

## Supported Genes & Drugs

| Gene | Drug | Example Risk |
|------|------|-------------|
| CYP2D6 | Codeine, Tramadol | Toxic (PM/URM) |
| CYP2C19 | Clopidogrel | Ineffective (PM) |
| CYP2C9 | Warfarin | Adjust Dosage (IM) |
| SLCO1B1 | Simvastatin | Toxic (PF) |
| TPMT | Azathioprine | Toxic (PM) |
| DPYD | Fluorouracil | Adjust Dosage (IM) |

## Environment Variables

```
GROQ_API_KEY=your_key_here
```

## License

MIT

---

Built for **RIFT 2026** 🚀
