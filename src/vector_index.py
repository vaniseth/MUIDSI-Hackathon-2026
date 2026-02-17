"""
Build FAISS vector index from document chunks
"""
import numpy as np
import faiss
import pickle
from pathlib import Path
from typing import List, Dict
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import FAISS_INDEX_PATH, METADATA_PATH, DOCSTORE_PATH
from src.archia_client import ArchiaClient
from src.document_processor import DocumentProcessor
from src.config import EMBEDDING_DIMENSION


class VectorIndexBuilder:
    """Build and manage FAISS vector index"""
    
    def __init__(self):
        self.client = ArchiaClient()
        self.doc_processor = DocumentProcessor()
        self.chunks = []
        self.index = None
    
    def load_or_create_chunks(self) -> List[Dict]:
        """Load existing chunks or create new ones"""
        chunks = self.doc_processor.load_chunks()
        
        if not chunks:
            print("No chunks found. Processing documents...")
            chunks = self.doc_processor.run()
        else:
            print(f"📖 Loaded {len(chunks)} existing chunks")
        
        self.chunks = chunks
        return chunks
    
    def create_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """Create embeddings using Archia"""
        print(f"\n🔮 Creating embeddings for {len(chunks)} chunks...")
        
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.client.create_embeddings_batch(texts)
        embeddings_array = np.array(embeddings, dtype='float32')
        
        print(f"✅ Embeddings shape: {embeddings_array.shape}")
        return embeddings_array
    
    def build_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build FAISS index"""
        print("\n🏗️  Building FAISS index...")
        
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
        index.add(embeddings)
        
        print(f"✅ Index built with {index.ntotal} vectors")
        
        self.index = index
        return index
    
    def save_index(self):
        """Save FAISS index and metadata"""
        FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        print(f"💾 Saved index: {FAISS_INDEX_PATH}")
        
        # Save metadata
        with open(METADATA_PATH, 'wb') as f:
            pickle.dump(self.chunks, f)
        print(f"💾 Saved metadata: {METADATA_PATH}")
    
    def load_index(self):
        """Load existing index"""
        if not FAISS_INDEX_PATH.exists() or not METADATA_PATH.exists():
            return None, None
        
        index = faiss.read_index(str(FAISS_INDEX_PATH))
        with open(METADATA_PATH, 'rb') as f:
            chunks = pickle.load(f)
        
        print(f"📖 Loaded index: {index.ntotal} vectors")
        print(f"📖 Loaded metadata: {len(chunks)} chunks")
        
        self.index = index
        self.chunks = chunks
        return index, chunks
    
    def build(self, force_rebuild: bool = False):
        """Complete build pipeline"""
        print("\n" + "="*60)
        print("🚀 FAISS Index Builder (Archia-powered)")
        print("="*60 + "\n")
        
        # Check existing index
        if not force_rebuild:
            index, chunks = self.load_index()
            if index is not None:
                print("\n✅ Index already exists!\n")
                return index, chunks
        
        # Load/create chunks
        chunks = self.load_or_create_chunks()
        if not chunks:
            print("\n❌ No documents to index!")
            return None, None
        
        # Create embeddings
        embeddings = self.create_embeddings(chunks)
        
        # Build index
        index = self.build_index(embeddings)
        
        # Save
        self.save_index()
        
        print("\n" + "="*60)
        print("✅ Index building complete!")
        print("="*60 + "\n")
        
        return index, chunks


def main():
    """Run the index builder"""
    builder = VectorIndexBuilder()
    index, chunks = builder.build(force_rebuild=True)
    
    if index:
        print(f"\n📊 Final Stats:")
        print(f"   Vectors: {index.ntotal}")
        print(f"   Dimension: {index.d}")
        print(f"   Chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
