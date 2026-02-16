"""
Document ingestion: PDF/TXT -> text chunks
"""
import json
from pathlib import Path
from typing import List, Dict
from pypdf import PdfReader
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import DOCS_DIR, DOCSTORE_PATH, CHUNK_SIZE


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    import re
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,!?;:()\-\']', '', text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    
    if len(words) <= chunk_size:
        return [text]
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) >= 50:
            chunks.append(' '.join(chunk_words))
    
    return chunks


class DocumentProcessor:
    """Process documents into chunks"""
    
    def __init__(self, docs_dir: Path = DOCS_DIR):
        self.docs_dir = docs_dir
    
    def load_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF"""
        try:
            reader = PdfReader(str(pdf_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading {pdf_path.name}: {e}")
            return ""
    
    def load_txt(self, txt_path: Path) -> str:
        """Load text file"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {txt_path.name}: {e}")
            return ""
    
    def process_document(self, filepath: Path) -> Dict:
        """Process a single document"""
        suffix = filepath.suffix.lower()
        
        if suffix == '.pdf':
            content = self.load_pdf(filepath)
        elif suffix == '.txt':
            content = self.load_txt(filepath)
        else:
            print(f"Unsupported file type: {suffix}")
            return None
        
        if not content:
            return None
        
        content = clean_text(content)
        
        return {
            'filename': filepath.name,
            'content': content,
            'word_count': len(content.split())
        }
    
    def load_all_documents(self) -> List[Dict]:
        """Load all documents from docs directory"""
        if not self.docs_dir.exists():
            print(f"⚠️  Docs directory not found: {self.docs_dir}")
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created {self.docs_dir}")
            print(f"➡️  Add your MU safety PDFs to: {self.docs_dir}")
            return []
        
        documents = []
        for filepath in self.docs_dir.iterdir():
            if filepath.suffix.lower() in ['.pdf', '.txt']:
                print(f"📄 Processing: {filepath.name}")
                doc = self.process_document(filepath)
                if doc:
                    documents.append(doc)
        
        print(f"✅ Loaded {len(documents)} documents")
        return documents
    
    def create_chunks(self, documents: List[Dict]) -> List[Dict]:
        """Create text chunks from documents"""
        all_chunks = []
        
        for doc in documents:
            chunks = chunk_text(doc['content'])
            
            for idx, chunk_text in enumerate(chunks):
                chunk = {
                    'chunk_id': f"{doc['filename']}_chunk_{idx}",
                    'text': chunk_text,
                    'source': doc['filename'],
                    'chunk_index': idx,
                    'word_count': len(chunk_text.split())
                }
                all_chunks.append(chunk)
        
        print(f"📦 Created {len(all_chunks)} chunks")
        return all_chunks
    
    def save_chunks(self, chunks: List[Dict], output_path: Path = DOCSTORE_PATH):
        """Save chunks to JSONL file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk) + '\n')
        
        print(f"💾 Saved to: {output_path}")
    
    def load_chunks(self, input_path: Path = DOCSTORE_PATH) -> List[Dict]:
        """Load chunks from JSONL file"""
        if not input_path.exists():
            return []
        
        chunks = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line))
        
        return chunks
    
    def run(self) -> List[Dict]:
        """Complete processing pipeline"""
        print("\n🔄 Processing documents...\n")
        documents = self.load_all_documents()
        
        if not documents:
            return []
        
        chunks = self.create_chunks(documents)
        self.save_chunks(chunks)
        print("\n✅ Processing complete!\n")
        return chunks
