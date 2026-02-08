"""Quick Gemini API connectivity test."""
import os
os.environ.setdefault("GEMINI_API_KEY", "")

from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    print("ERROR: GEMINI_API_KEY not set")
    exit(1)

client = genai.Client(api_key=api_key)

# --- Chat Test ---
print("Chat test...")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="SAP S/4HANA donusumunde en kritik 3 risk nedir? Kisa cevap ver.",
    config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=300),
)
print("CHAT OK")
print(response.text[:500])
print()

# --- Embedding Test ---
print("Embedding test...")
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=["SAP FI modulu GL posting", "SAP MM satinalma siparis"],
    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=1536),
)
vecs = result.embeddings
print(f"EMBEDDING OK - {len(vecs)} vectors, dim={len(vecs[0].values)}")
print(f"Sample (first 5 values): {vecs[0].values[:5]}")
print()
print("ALL TESTS PASSED - Gemini Free Tier is working!")
