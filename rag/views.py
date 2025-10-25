"""
API views and template views for Taiwan Patent RAG system.
"""
import logging

from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.rag_engine import RAGEngine
from .serializers import QuerySerializer, QueryResponseSerializer, HealthSerializer

logger = logging.getLogger(__name__)


# ========== Template Views ==========

def index_view(request):
    """
    Main page with query interface.
    """
    return render(request, 'rag/index.html')


def query_page_view(request):
    """
    Process query from web form.
    """
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()

        if not question:
            return render(request, 'rag/index.html', {
                'error': '請輸入問題'
            })

        try:
            # Initialize RAG engine
            rag_engine = RAGEngine()

            # Process query
            result = rag_engine.query(question)

            return render(request, 'rag/index.html', {
                'question': question,
                'answer': result['answer'],
                'sources': result['sources'],
                'response_time_ms': result['response_time_ms']
            })

        except ValueError as e:
            logger.error(f"ValueError in query: {e}")
            return render(request, 'rag/index.html', {
                'question': question,
                'error': str(e)
            })

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return render(request, 'rag/index.html', {
                'question': question,
                'error': '處理問題時發生錯誤，請稍後再試。'
            })

    return render(request, 'rag/index.html')


def health_page_view(request):
    """
    Health check page.
    """
    try:
        rag_engine = RAGEngine()
        stats = rag_engine.get_stats()

        return render(request, 'rag/health.html', {
            'status': 'healthy' if 'error' not in stats else 'degraded',
            'vector_db_stats': stats
        })

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return render(request, 'rag/health.html', {
            'status': 'unhealthy',
            'error': str(e)
        })


# ========== API Views ==========


@api_view(['POST'])
def query_view(request):
    """
    Query endpoint for asking patent-related questions.

    POST /api/query/
    Body: {"question": "請找出與AI相關的專利"}

    Returns: {
        "answer": "...",
        "sources": [...],
        "response_time_ms": 1234
    }
    """
    serializer = QuerySerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    question = serializer.validated_data['question']

    try:
        # Initialize RAG engine
        rag_engine = RAGEngine()

        # Process query
        result = rag_engine.query(question)

        # Serialize response
        response_serializer = QueryResponseSerializer(data=result)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Invalid response format'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except ValueError as e:
        logger.error(f"ValueError in query: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return Response(
            {'error': 'An error occurred while processing your question. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_view(request):
    """
    Health check endpoint.

    GET /api/health/

    Returns: {
        "status": "healthy",
        "vector_db_stats": {...}
    }
    """
    try:
        rag_engine = RAGEngine()
        stats = rag_engine.get_stats()

        health_data = {
            'status': 'healthy' if 'error' not in stats else 'degraded',
            'vector_db_stats': stats
        }

        serializer = HealthSerializer(data=health_data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'status': 'unhealthy', 'error': serializer.errors},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            {'status': 'unhealthy', 'error': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
