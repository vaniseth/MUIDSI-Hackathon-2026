"""
Archia API Client
Uses both OpenAI SDK (for OpenAI-compatible endpoints) and Anthropic SDK (for Claude)
"""
from openai import OpenAI
from anthropic import Anthropic
from typing import List, Dict
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.config import ARCHIA_TOKEN, ARCHIA_BASE_URL, CHAT_MODEL, EMBEDDING_MODEL


class ArchiaClient:
    """
    Unified client for Archia API
    Supports both OpenAI-compatible and Anthropic endpoints
    """
    
    def __init__(self, api_key: str = ARCHIA_TOKEN, base_url: str = ARCHIA_BASE_URL):
        if not api_key:
            raise ValueError("Archia API token not found. Set ARCHIA_TOKEN in .env file")
        
        # OpenAI-compatible client (for embeddings and OpenAI models)
        self.openai_client = OpenAI(
            api_key="not-used",  # Archia doesn't use this
            base_url=base_url,
            default_headers={
                "Authorization": f"Bearer {api_key}"
            }
        )
        
        # Anthropic client (for Claude models via Archia)
        # Using Anthropic SDK with Archia base URL
        self.anthropic_client = Anthropic(
            api_key=api_key,
            base_url="https://api.archia.io/v1"  # Archia's Anthropic-compatible endpoint
        )
        
        self.chat_model = CHAT_MODEL
        self.embedding_model = EMBEDDING_MODEL
        print("✅ Archia client initialized")
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding using Archia"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error creating embedding: {e}")
            return []
    
    def create_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Create embeddings for multiple texts"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                print(f"✅ Embeddings: {len(all_embeddings)}/{len(texts)}")
            except Exception as e:
                print(f"Error in batch {i}: {e}")
                all_embeddings.extend([[0.0] * 1536] * len(batch))
        
        return all_embeddings
    
    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        Chat using Claude via Archia (Anthropic SDK)
        """
        try:
            message = self.anthropic_client.messages.create(
                model=self.chat_model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_message}"}
                ],
                temperature=temperature
            )
            return message.content[0].text
        except Exception as e:
            print(f"Error calling Archia API: {e}")
            return f"Error: {str(e)}"
    
    def call_agent(self, agent_name: str, user_message: str, temperature: float = 0.7) -> str:
        """
        Call a named agent created in Archia console
        
        Args:
            agent_name: Name of agent (e.g., "agent:safety_copilot")
            user_message: User's query
            temperature: Sampling temperature
            
        Returns:
            Agent response
        """
        try:
            # Using Archia's responses endpoint for agents
            response = self.openai_client.chat.completions.create(
                model=agent_name,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling agent {agent_name}: {e}")
            # Fallback to direct Claude call
            return self.chat(
                system_prompt="You are a helpful campus safety assistant.",
                user_message=user_message,
                temperature=temperature
            )
