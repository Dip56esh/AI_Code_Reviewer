#  AI Code Reviewer

A FastAPI-powered tool that reviews code snippets for bugs and improvements using a free AI model (Groq ). Comes with a clean web UI.

---

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Add your Groq API key to `.env`**
```
PROVIDER=groq
GROQ_API_KEY=your_key_here
```
**3. Start the server**
```bash
uvicorn main:app --reload
```

**4. Open `index.html` in your browser**

That's it. Paste code → click **Run AI Review**.

---

## API

### `POST /review`

```json
{
  "code": "def divide(a, b): return a / b",
  "language": "python",
  "context": "optional description"
}
```

**Response:**
```json
{
  "summary": "Missing division by zero guard.",
  "overall_score": 5,
  "provider": "groq",
  "issues": [
    {
      "line": "return a / b",
      "severity": "high",
      "type": "bug",
      "description": "Will raise ZeroDivisionError if b is 0.",
      "suggestion": "Add: if b == 0: raise ValueError('Cannot divide by zero')"
    }
  ],
  "disclaimer": "AI-generated. Verify manually before applying."
}
```

Interactive docs available at `http://localhost:8000/docs`

---

## Stack

- **Backend** — Python, FastAPI, httpx
- **AI** — Groq API (Llama 3 70B) 
- **Frontend** — Vanilla HTML/CSS/JS 
