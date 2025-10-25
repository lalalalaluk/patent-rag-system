"""
Taiwan Patent RAG Engine - Core retrieval-augmented generation logic for patent search.
Uses Google Gemini for free LLM access.
"""
import json
import logging
import time
from typing import List, Dict, Optional

import chromadb
from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI

from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval-Augmented Generation engine for Taiwan Patent search and Q&A.
    Uses Google Gemini (free) for LLM.
    """

    COLLECTION_NAME = "taiwan_patents"

    PROMPT_TEMPLATE = """你是一個台灣專利搜尋與分析的專業助手。

請仔細分析以下專利文件，**只回答與問題直接相關的專利**。

重要規則:
1. 只討論與問題主題有直接技術關聯的專利
2. 如果某個專利與問題無直接關聯,請完全忽略它,不要提及
3. 請用繁體中文回答
4. 提供相關專利的詳細資訊（專利號、名稱、申請人、技術說明）
5. 在回答的最後，請用以下格式列出所有相關的專利號碼：
   相關專利號: [專利號1, 專利號2, ...]
   如果沒有相關專利，請寫：相關專利號: []

專利文件：
{context}

問題：{question}

回答（只包含真正相關的專利資訊）："""

    def __init__(self):
        """Initialize the RAG engine."""
        # Initialize embedding service (local, free)
        self.embedding_service = EmbeddingService()

        # Initialize ChromaDB client
        chroma_url = f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}"
        logger.info(f"Connecting to ChromaDB at {chroma_url}")

        self.chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=int(settings.CHROMA_PORT)
        )

        # Initialize Gemini LLM (free)
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
            convert_system_message_to_human=True
        )

        logger.info("RAG Engine initialized successfully with Gemini")

    def create_collection(self, reset: bool = False):
        """
        Create or get the vector collection.

        Args:
            reset: If True, delete existing collection and create new one
        """
        try:
            if reset:
                try:
                    self.chroma_client.delete_collection(name=self.COLLECTION_NAME)
                    logger.info(f"Deleted existing collection: {self.COLLECTION_NAME}")
                except Exception:
                    pass

            self.collection = self.chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "Taiwan Patent Office documents"}
            )
            logger.info(f"Collection ready: {self.COLLECTION_NAME}")

        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise

    def index_documents(self, sections: Optional[List[str]] = None):
        """
        Index processed documents into the vector database.

        Args:
            sections: List of sections to index (default: all available)
        """
        # Create/reset collection
        self.create_collection(reset=True)

        # Find available section files if not specified
        if sections is None:
            sections = []
            for file in settings.PROCESSED_DATA_DIR.glob('*_chunks.json'):
                section = file.stem.replace('_chunks', '')
                sections.append(section)

        logger.info(f"Indexing sections: {sections}")

        total_indexed = 0

        for section in sections:
            chunk_file = settings.PROCESSED_DATA_DIR / f'{section}_chunks.json'

            if not chunk_file.exists():
                logger.warning(f"Chunk file not found: {chunk_file}")
                continue

            # Load chunks
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)

            logger.info(f"Indexing {len(chunks)} chunks from {section}")

            # Process in batches
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]

                # Prepare data for ChromaDB
                texts = [chunk['text'] for chunk in batch]
                metadatas = [chunk['metadata'] for chunk in batch]
                ids = [f"{section}_{j}" for j in range(i, i + len(batch))]

                # Generate embeddings
                embeddings = self.embedding_service.embed_documents(texts)

                # Add to collection
                self.collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )

                total_indexed += len(batch)
                logger.info(f"Indexed {total_indexed} chunks so far...")

        logger.info(f"Indexing complete! Total chunks indexed: {total_indexed}")

    def retrieve_relevant_docs(self, question: str, top_k: int = None) -> List[Dict]:
        """
        Retrieve relevant documents for a question.

        Args:
            question: User question
            top_k: Number of documents to retrieve

        Returns:
            List of relevant document dictionaries
        """
        top_k = top_k or settings.TOP_K_RESULTS

        # Get collection
        try:
            self.collection = self.chroma_client.get_collection(name=self.COLLECTION_NAME)
        except Exception as e:
            logger.error(f"Collection not found: {e}")
            raise ValueError("Vector database not initialized. Please run build_index first.")

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(question)

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        # Format results
        documents = []
        if results['documents'] and results['documents'][0]:
            for i, doc_text in enumerate(results['documents'][0]):
                documents.append({
                    'text': doc_text,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None
                })

        logger.info(f"Retrieved {len(documents)} relevant documents")
        return documents

    def generate_answer(self, question: str, context_docs: List[Dict]) -> str:
        """
        Generate an answer using Gemini based on retrieved patent context.

        Args:
            question: User question
            context_docs: Retrieved relevant patent documents

        Returns:
            Generated answer
        """
        # Build context from retrieved patent documents
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            metadata = doc['metadata']
            patent_num = metadata.get('patent_number', '未知')
            title = metadata.get('title', '未知')
            applicant = metadata.get('applicant', '未知')
            part = metadata.get('heading', metadata.get('part', ''))

            context_parts.append(
                f"[{i}] 專利號: {patent_num} | 名稱: {title} | 申請人: {applicant} | 部分: {part}\n"
                f"{doc['text']}\n"
            )

        context = "\n---\n".join(context_parts)

        # Build prompt
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            question=question
        )

        # Generate answer
        try:
            response = self.llm.invoke(prompt)
            answer = response.content
            return answer

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def query(self, question: str) -> Dict:
        """
        Main query method - retrieve and generate answer.

        Args:
            question: User question

        Returns:
            Dictionary with answer and metadata
        """
        start_time = time.time()

        logger.info(f"Processing query: {question}")

        # Retrieve relevant documents
        relevant_docs = self.retrieve_relevant_docs(question)

        if not relevant_docs:
            return {
                'answer': "I couldn't find relevant information in the Python documentation to answer your question.",
                'sources': [],
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

        # Generate answer
        answer = self.generate_answer(question, relevant_docs)

        # Extract relevant patent numbers from AI response
        relevant_patent_numbers = self._extract_relevant_patents(answer)

        # Prepare sources - only include patents that AI deemed relevant
        sources = []
        seen_patents = set()
        for doc in relevant_docs:
            metadata = doc['metadata']
            patent_num = metadata.get('patent_number', '')

            # Only include if AI identified this patent as relevant
            if patent_num and patent_num not in seen_patents and patent_num in relevant_patent_numbers:
                sources.append({
                    'title': metadata.get('title', 'Unknown'),
                    'patent_number': patent_num,
                    'applicant': metadata.get('applicant', ''),
                    'ipc_classification': metadata.get('ipc_classification', ''),
                    'section': metadata.get('section', 'Unknown'),
                    'excerpt': doc['text'][:200] + '...' if len(doc['text']) > 200 else doc['text']
                })
                seen_patents.add(patent_num)

        response_time = int((time.time() - start_time) * 1000)

        logger.info(f"Query completed in {response_time}ms - Found {len(sources)} relevant patents")

        return {
            'answer': answer,
            'sources': sources,
            'response_time_ms': response_time
        }

    def _extract_relevant_patents(self, answer: str) -> set:
        """
        Extract relevant patent numbers from AI's answer.

        Args:
            answer: AI generated answer

        Returns:
            Set of relevant patent numbers
        """
        import re

        relevant_patents = set()

        # Look for the "相關專利號: [...]" pattern at the end
        pattern = r'相關專利號:\s*\[(.*?)\]'
        match = re.search(pattern, answer)

        if match:
            patents_str = match.group(1)
            # Extract patent numbers (format: I123456, M123456, etc.)
            patent_numbers = re.findall(r'[IMD]\d+', patents_str)
            relevant_patents.update(patent_numbers)
            logger.info(f"AI identified relevant patents: {relevant_patents}")
        else:
            # Fallback: extract all patent numbers mentioned in the answer
            # This catches patents mentioned in the main text
            patent_numbers = re.findall(r'專利號:\s*([IMD]\d+)', answer)
            relevant_patents.update(patent_numbers)
            logger.info(f"Extracted patents from answer text: {relevant_patents}")

        return relevant_patents

    def get_stats(self) -> Dict:
        """
        Get statistics about the vector database.

        Returns:
            Statistics dictionary
        """
        try:
            self.collection = self.chroma_client.get_collection(name=self.COLLECTION_NAME)
            count = self.collection.count()

            return {
                'total_documents': count,
                'collection_name': self.COLLECTION_NAME,
                'embedding_dimension': self.embedding_service.get_embedding_dimension(),
                'embedding_model': self.embedding_service.model_name
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
