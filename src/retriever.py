"""
Retrieve relevant documents using FAISS vector search
"""
import numpy as np
from typing import List, Dict, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.config import TOP_K_DOCUMENTS
from src.archia_client import ArchiaClient
from src.vector_index import VectorIndexBuilder


class DocumentRetriever:
    """Retrieve relevant documents using vector similarity"""
    
    def __init__(self):
        self.client = ArchiaClient()
        self.index = None
        self.chunks = None
        self.load()
    
    def load(self):
        """Load FAISS index and metadata"""
        builder = VectorIndexBuilder()
        self.index, self.chunks = builder.load_index()
        
        if self.index is None:
            print("⚠️  Index not found. Building...")
            self.index, self.chunks = builder.build()
    
    def retrieve(self, query: str, top_k: int = TOP_K_DOCUMENTS) -> List[Dict]:
        """
        Retrieve top-k most relevant documents
        
        Args:
            query: Search query
            top_k: Number of documents to retrieve
            
        Returns:
            List of relevant chunks with scores
        """
        if self.index is None or not self.chunks:
            print("❌ Index not loaded")
            return []
        
        # Create query embedding
        query_embedding = self.client.create_embedding(query)
        if not query_embedding:
            return []
        
        # Convert to numpy array
        query_vector = np.array([query_embedding], dtype='float32')
        
        # Search FAISS index
        distances, indices = self.index.search(query_vector, top_k)
        
        # Compile results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= len(self.chunks):
                continue
            
            # Convert distance to similarity score
            similarity_score = 1 / (1 + dist)
            
            chunk = self.chunks[idx].copy()
            chunk['similarity_score'] = float(similarity_score)
            chunk['distance'] = float(dist)
            chunk['rank'] = i + 1
            
            results.append(chunk)
        
        return results
    
    def retrieve_with_context(self, query: str, top_k: int = TOP_K_DOCUMENTS) -> Tuple[List[Dict], str]:
        """
        Retrieve documents and format as context string
        
        Returns:
            Tuple of (results, formatted_context)
        """
        results = self.retrieve(query, top_k=top_k)
        
        if not results:
            return [], "No relevant information found."
        
        # Format context
        context_parts = []
        for i, result in enumerate(results):
            context_parts.append(
                f"[Source {i+1}: {result['source']}] (Relevance: {result['similarity_score']:.2f})\n{result['text']}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        return results, context
    
    def get_sources(self, results: List[Dict]) -> List[str]:
        """Extract unique source documents"""
        sources = set(r['source'] for r in results)
        return sorted(list(sources))
