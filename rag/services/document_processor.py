"""
Document processing service for chunking and preparing patent documents for embeddings.
"""
import json
import logging
import re
from typing import List, Dict
from pathlib import Path

from django.conf import settings
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process and chunk patent documents for RAG system."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize the document processor.

        Args:
            chunk_size: Size of each text chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def process_document(self, document: Dict) -> List[Dict]:
        """
        Process a single patent document into chunks.

        Args:
            document: Patent document dictionary with keys:
                     - patent_number, title, abstract, description, claims, etc.
                     OR legacy format: url, title, content, section, sections

        Returns:
            List of chunk dictionaries
        """
        processed_chunks = []

        # Handle patent document format
        if 'patent_number' in document:
            # New patent format
            patent_number = document.get('patent_number', '')
            title = document.get('title', '')
            section = document.get('patent_type', 'all')

            # Combine different parts of the patent
            parts_to_chunk = []

            # 1. Abstract (摘要)
            if document.get('abstract'):
                parts_to_chunk.append({
                    'content': self._clean_text(document['abstract']),
                    'part': 'abstract',
                    'heading': '摘要'
                })

            # 2. Description (說明書)
            if document.get('description'):
                parts_to_chunk.append({
                    'content': self._clean_text(document['description']),
                    'part': 'description',
                    'heading': '說明書'
                })

            # 3. Claims (申請專利範圍)
            if document.get('claims'):
                if isinstance(document['claims'], list):
                    claims_text = '\n'.join(document['claims'])
                else:
                    claims_text = document['claims']
                parts_to_chunk.append({
                    'content': self._clean_text(claims_text),
                    'part': 'claims',
                    'heading': '申請專利範圍'
                })

            # Process each part
            for part_data in parts_to_chunk:
                chunks = self.text_splitter.split_text(part_data['content'])

                for i, chunk_text in enumerate(chunks):
                    chunk = {
                        'text': chunk_text,
                        'metadata': {
                            'patent_number': patent_number,
                            'title': title,
                            'heading': part_data['heading'],
                            'part': part_data['part'],
                            'section': section,
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'source_url': document.get('url', ''),
                            'inventor': document.get('inventor', ''),
                            'applicant': document.get('applicant', ''),
                            'application_date': document.get('application_date', ''),
                            'ipc_classification': document.get('ipc_classification', ''),
                        }
                    }
                    processed_chunks.append(chunk)

        # Legacy format support (for backward compatibility)
        elif 'sections' in document and document['sections']:
            for doc_section in document['sections']:
                content = self._clean_text(doc_section['content'])
                chunks = self.text_splitter.split_text(content)

                for i, chunk_text in enumerate(chunks):
                    chunk = {
                        'text': chunk_text,
                        'metadata': {
                            'source_url': doc_section['url'],  # URL with anchor
                            'title': document['title'],
                            'heading': doc_section.get('heading', ''),  # Section heading
                            'section': document['section'],
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                        }
                    }
                    processed_chunks.append(chunk)
        else:
            # Fallback: use full document content (backward compatibility)
            content = self._clean_text(document.get('content', ''))
            chunks = self.text_splitter.split_text(content)

            for i, chunk_text in enumerate(chunks):
                chunk = {
                    'text': chunk_text,
                    'metadata': {
                        'source_url': document.get('url', ''),
                        'title': document.get('title', ''),
                        'section': document.get('section', ''),
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                    }
                }
                processed_chunks.append(chunk)

        return processed_chunks

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Remove special characters but keep code-like formatting
        text = text.strip()

        return text

    def process_section(self, section: str) -> List[Dict]:
        """
        Process all patent documents from a category.

        Args:
            section: Patent category (e.g., 'invention', 'utility', 'design')

        Returns:
            List of all chunks from the category
        """
        input_file = settings.RAW_DATA_DIR / f'{section}_docs.json'

        if not input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            return []

        # Load documents
        with open(input_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)

        logger.info(f"Processing {len(documents)} documents from {section}")

        # Process each document
        all_chunks = []
        for doc in documents:
            chunks = self.process_document(doc)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {section}")
        return all_chunks

    def save_processed_chunks(self, chunks: List[Dict], section: str):
        """
        Save processed chunks to JSON file.

        Args:
            chunks: List of chunk dictionaries
            section: Section name
        """
        output_file = settings.PROCESSED_DATA_DIR / f'{section}_chunks.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(chunks)} chunks to {output_file}")

    def process_all_sections(self, sections: List[str] = None) -> Dict[str, List[Dict]]:
        """
        Process all sections.

        Args:
            sections: List of section names to process (default: all available)

        Returns:
            Dictionary mapping section names to chunk lists
        """
        if sections is None:
            # Find all available section files
            sections = []
            for file in settings.RAW_DATA_DIR.glob('*_docs.json'):
                section = file.stem.replace('_docs', '')
                sections.append(section)

        all_processed = {}

        for section in sections:
            logger.info(f"Processing section: {section}")
            chunks = self.process_section(section)
            all_processed[section] = chunks
            self.save_processed_chunks(chunks, section)

        total_chunks = sum(len(chunks) for chunks in all_processed.values())
        logger.info(f"Total chunks processed: {total_chunks}")

        return all_processed

    def get_chunk_statistics(self, chunks: List[Dict]) -> Dict:
        """
        Get statistics about chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {}

        chunk_lengths = [len(chunk['text']) for chunk in chunks]

        return {
            'total_chunks': len(chunks),
            'avg_chunk_length': sum(chunk_lengths) / len(chunk_lengths),
            'min_chunk_length': min(chunk_lengths),
            'max_chunk_length': max(chunk_lengths),
            'sections': list(set(chunk['metadata']['section'] for chunk in chunks))
        }
