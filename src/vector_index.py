"""
Build FAISS vector index from ALL sources:
  1. Policy documents (PDF + TXT from data/docs/)  ← existing
  2. Crime data summaries (from crime CSVs)         ← new
  3. TIGER road sightline summaries                 ← new
  4. VIIRS lighting summaries                       ← new
  5. ROI research citation summaries                ← new

Run this whenever:
  - You add new documents to data/docs/
  - You add new crime data to data/crime_data/
  - You download the VIIRS .tif file
  - You add the TIGER shapefile
"""

import numpy as np
import faiss
import pickle
import json
from pathlib import Path
from typing import List, Dict
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import (FAISS_INDEX_PATH, METADATA_PATH,
                         DOCSTORE_PATH, EMBEDDING_DIMENSION)
from src.archia_client import ArchiaClient
from src.document_processor import DocumentProcessor
from src.data_summarizer import DataSummarizer


class VectorIndexBuilder:
    """
    Builds and manages FAISS vector index over both policy documents
    and structured data summaries (crime, TIGER, VIIRS, research).
    """

    def __init__(self):
        self.client        = ArchiaClient()
        self.doc_processor = DocumentProcessor()
        self.summarizer    = DataSummarizer()
        self.chunks: List[Dict] = []
        self.index = None

    # ── Chunk loading ─────────────────────────────────────────────────────────

    def load_document_chunks(self) -> List[Dict]:
        """Load or create chunks from PDF/TXT policy documents."""
        chunks = self.doc_processor.load_chunks()
        if not chunks:
            print("No document chunks found — processing docs/...")
            chunks = self.doc_processor.run()
        else:
            print(f"  Loaded {len(chunks)} existing document chunks")
        return chunks

    def load_data_chunks(self, force_rebuild: bool = False) -> List[Dict]:
        """
        Generate text chunks from structured data sources.
        Checks docstore first to avoid regenerating if already present.
        """
        if not force_rebuild and DOCSTORE_PATH.exists():
            # Check if data chunks already exist in docstore
            existing_data_chunks = []
            try:
                with open(DOCSTORE_PATH, 'r') as f:
                    for line in f:
                        try:
                            chunk = json.loads(line)
                            if chunk.get('type') == 'data_summary':
                                existing_data_chunks.append(chunk)
                        except Exception:
                            continue
                if existing_data_chunks:
                    print(f"  Loaded {len(existing_data_chunks)} existing data summary chunks")
                    return existing_data_chunks
            except Exception:
                pass

        print("  Generating data summary chunks...")
        data_chunks = self.summarizer.run(
            include_crime=True,
            include_tiger=True,
            include_viirs=True,
            include_research=True,
        )
        # Save to docstore for future runs
        self.summarizer.save_chunks(data_chunks)
        return data_chunks

    def load_all_chunks(self, force_rebuild: bool = False) -> List[Dict]:
        """Load all chunks: policy documents + structured data summaries."""
        print("\n" + "-" * 50)
        print("  Loading document chunks (PDF/TXT)...")
        doc_chunks  = self.load_document_chunks()

        print("\n  Loading data summary chunks (CSV/TIGER/VIIRS)...")
        data_chunks = self.load_data_chunks(force_rebuild=force_rebuild)

        all_chunks = doc_chunks + data_chunks

        # Deduplicate by chunk_id
        seen = set()
        deduped = []
        for chunk in all_chunks:
            cid = chunk.get('chunk_id', chunk.get('id', ''))
            if cid not in seen:
                seen.add(cid)
                deduped.append(chunk)

        dupes = len(all_chunks) - len(deduped)
        if dupes:
            print(f"  Removed {dupes} duplicate chunks")

        print(f"\n  Total chunks for indexing: {len(deduped)}")
        print(f"    Document chunks: {len(doc_chunks)}")
        print(f"    Data summary chunks: {len(data_chunks)}")
        self.chunks = deduped
        return deduped

    # ── Embedding ─────────────────────────────────────────────────────────────

    def create_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """Create embeddings for all chunks using local sentence-transformers."""
        print(f"\n  Creating embeddings for {len(chunks)} chunks...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.client.create_embeddings_batch(texts)
        arr = np.array(embeddings, dtype='float32')
        print(f"  Embeddings shape: {arr.shape}")
        return arr

    # ── Index building ────────────────────────────────────────────────────────

    def build_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build FAISS flat L2 index from embeddings."""
        print("\n  Building FAISS index...")
        index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
        index.add(embeddings)
        print(f"  Index built: {index.ntotal} vectors, dimension {index.d}")
        self.index = index
        return index

    def save_index(self):
        """Save FAISS index and chunk metadata."""
        FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        print(f"  Saved index:    {FAISS_INDEX_PATH}")
        with open(METADATA_PATH, 'wb') as f:
            pickle.dump(self.chunks, f)
        print(f"  Saved metadata: {METADATA_PATH} ({len(self.chunks)} chunks)")

    def load_index(self):
        """Load existing FAISS index and metadata."""
        if not FAISS_INDEX_PATH.exists() or not METADATA_PATH.exists():
            return None, None
        index = faiss.read_index(str(FAISS_INDEX_PATH))
        with open(METADATA_PATH, 'rb') as f:
            chunks = pickle.load(f)
        print(f"  Loaded index:    {index.ntotal} vectors")
        print(f"  Loaded metadata: {len(chunks)} chunks")
        self.index  = index
        self.chunks = chunks
        return index, chunks

    # ── Stats ─────────────────────────────────────────────────────────────────

    def print_index_stats(self):
        """Print breakdown of what's in the index."""
        if not self.chunks:
            return
        doc_chunks  = [c for c in self.chunks if c.get('type') != 'data_summary']
        data_chunks = [c for c in self.chunks if c.get('type') == 'data_summary']

        # Source breakdown for data chunks
        sources = {}
        for c in data_chunks:
            src = c.get('source', 'unknown')
            key = src.split('_')[0] if '_' in src else src
            sources[key] = sources.get(key, 0) + 1

        print(f"\n  Index contents:")
        print(f"    Policy document chunks: {len(doc_chunks)}")
        print(f"    Data summary chunks:    {len(data_chunks)}")
        if sources:
            for src, cnt in sorted(sources.items()):
                print(f"      {src}: {cnt} chunks")
        print(f"    Total vectors: {self.index.ntotal if self.index else 'N/A'}")

    # ── Main build pipeline ───────────────────────────────────────────────────

    def build(self, force_rebuild: bool = False):
        """Complete build pipeline: load → embed → index → save."""
        print("\n" + "=" * 55)
        print("  MizzouSafe — FAISS Vector Index Builder")
        print("=" * 55)

        # Return existing index if not forcing rebuild
        if not force_rebuild:
            index, chunks = self.load_index()
            if index is not None:
                print("\n  Index already exists — use --force to rebuild")
                self.print_index_stats()
                return index, chunks

        # Load all chunks
        chunks = self.load_all_chunks(force_rebuild=force_rebuild)
        if not chunks:
            print("\n  No chunks to index")
            return None, None

        # Embed
        embeddings = self.create_embeddings(chunks)

        # Build FAISS index
        index = self.build_index(embeddings)

        # Save
        self.save_index()

        self.print_index_stats()

        print("\n" + "=" * 55)
        print("  Index build complete!")
        print("=" * 55 + "\n")
        return index, chunks


def main():
    import argparse
    parser = argparse.ArgumentParser(description='MizzouSafe FAISS Index Builder')
    parser.add_argument('--force', action='store_true',
                        help='Force rebuild even if index exists')
    parser.add_argument('--data-only', action='store_true',
                        help='Only regenerate data summary chunks, then rebuild')
    args = parser.parse_args()

    builder = VectorIndexBuilder()

    if args.data_only:
        print("\n  Regenerating data summary chunks only...")
        # Clear existing data chunks from docstore
        if DOCSTORE_PATH.exists():
            non_data = []
            with open(DOCSTORE_PATH, 'r') as f:
                for line in f:
                    try:
                        chunk = json.loads(line)
                        if chunk.get('type') != 'data_summary':
                            non_data.append(chunk)
                    except Exception:
                        continue
            with open(DOCSTORE_PATH, 'w') as f:
                for chunk in non_data:
                    f.write(json.dumps(chunk) + '\n')
            print(f"  Cleared data chunks from docstore, kept {len(non_data)} doc chunks")
        args.force = True

    index, chunks = builder.build(force_rebuild=args.force)

    if index:
        print(f"\n  Final index stats:")
        print(f"    Vectors:   {index.ntotal}")
        print(f"    Dimension: {index.d}")
        print(f"    Chunks:    {len(chunks)}")


if __name__ == '__main__':
    main()