from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import os


PROVIDER     = os.getenv("PROVIDER", "groq").lower()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

app = FastAPI(
    title="AI Code Reviewer",
    description="Reviews code for bugs and improvements — powered by Groq or Ollama (free!)",
    version="2.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    context: str = ""

class ReviewIssue(BaseModel):
    line: str
    severity: str
    type: str
    description: str
    suggestion: str

class CodeReviewResponse(BaseModel):
    language: str
    provider: str
    summary: str
    issues: list[ReviewIssue]
    overall_score: int
    disclaimer: str


def build_prompt(code: str, language: str, context: str) -> str:
    ctx = f"\nAdditional context: {context}" if context else ""
    return f"""You are a senior software engineer performing a thorough code review.
Analyse the following {language} code and identify:
1. Bugs or potential runtime errors
2. Suggestions for improvement (readability, performance, best practices)
{ctx}

Return ONLY a valid JSON object — no markdown, no explanation, just raw JSON:
{{
  "summary": "one sentence overall summary",
  "overall_score": <integer 1-10>,
  "issues": [
    {{
      "line": "the relevant code line or snippet",
      "severity": "high|medium|low",
      "type": "bug|improvement",
      "description": "what the problem is",
      "suggestion": "how to fix or improve it"
    }}
  ]
}}

Code to review:
```{language}
{code}
```"""


def parse_ai_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[:-1])
    return json.loads(cleaned.strip())


async def call_groq(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(GROQ_API_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Groq API error: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"]


@app.get("/")
def root():
    return {
        "message": "AI Code Reviewer API",
        "provider": PROVIDER,
        "model": GROQ_MODEL if PROVIDER == "groq" else None,
        "docs": "/docs",
    }


@app.post("/review", response_model=CodeReviewResponse)
async def review_code(request: CodeReviewRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if len(request.code) > 8000:
        raise HTTPException(status_code=400, detail="Code too long (max 8000 chars)")

    prompt = build_prompt(request.code, request.language, request.context)

    if PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY not set. Get one free at console.groq.com")
        raw = await call_groq(prompt)
    else:
        raise HTTPException(status_code=500, detail=f"Unknown PROVIDER: {PROVIDER}")

    try:
        parsed = parse_ai_response(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}")

    if not {"summary", "overall_score", "issues"}.issubset(parsed.keys()):
        raise HTTPException(status_code=502, detail="AI response missing required fields")

    issues = [
        ReviewIssue(
            line=str(i.get("line", "")),
            severity=i.get("severity", "low"),
            type=i.get("type", "improvement"),
            description=i.get("description", ""),
            suggestion=i.get("suggestion", ""),
        )
        for i in parsed.get("issues", []) if isinstance(i, dict)
    ]

    return CodeReviewResponse(
        language=request.language,
        provider=PROVIDER,
        summary=parsed["summary"],
        issues=issues,
        overall_score=int(parsed.get("overall_score", 5)),
        disclaimer=(
            "AI-generated review. Always apply human judgment before acting on suggestions. "
            "Verify business logic, security-critical paths, and edge cases manually."
        )
    )