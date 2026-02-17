"""
Archia API Client
- Chat: Uses Archia's responses endpoint with correct system_name models
- Embeddings: Uses sentence-transformers locally (Archia has no embedding models)
"""
from openai import OpenAI
from typing import List
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.config import ARCHIA_TOKEN, ARCHIA_BASE_URL, CHAT_MODEL, EMBEDDING_MODEL


class ArchiaClient:

    def __init__(self, api_key: str = ARCHIA_TOKEN, base_url: str = ARCHIA_BASE_URL):
        if not api_key:
            raise ValueError("ARCHIA_TOKEN not set in .env")

        # Archia OpenAI-compatible client for chat
        self.openai_client = OpenAI(
            base_url=base_url,
            api_key="not-used",
            default_headers={"Authorization": f"Bearer {api_key}"}
        )

        # Local sentence-transformers for embeddings (Archia has no embedding models)
        print("🔄 Loading embedding model (sentence-transformers)...")
        from sentence_transformers import SentenceTransformer
        self.embedding_model_local = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded")

        self.chat_model = CHAT_MODEL
        print("✅ Archia client initialized")

    def create_embedding(self, text: str) -> List[float]:
        """Create embedding using local sentence-transformers"""
        embedding = self.embedding_model_local.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def create_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Create embeddings for multiple texts using local model"""
        print(f"🔮 Creating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_model_local.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True
        )
        print(f"✅ Embeddings complete: {len(embeddings)} vectors")
        return embeddings.tolist()

    def chat(self, system_prompt: str, user_message: str,
         temperature: float = 0.7, max_tokens: int = 2000) -> str:
         try:
            response = self.openai_client.responses.create(
                model=self.chat_model,
                instructions=system_prompt,
                input=user_message,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            # print("DEBUG response:", response)  # ← add this
            return response.output[0].content[0].text
         except Exception as e:
            print(f"❌ Archia chat error: {e}")
            return f"Error: {str(e)}"
