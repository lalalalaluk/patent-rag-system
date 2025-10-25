"""
Serializers for RAG API.
"""
from rest_framework import serializers


class QuerySerializer(serializers.Serializer):
    """Serializer for query requests."""
    question = serializers.CharField(
        required=True,
        max_length=500,
        help_text="The patent-related question to ask"
    )


class SourceSerializer(serializers.Serializer):
    """Serializer for patent document sources."""
    title = serializers.CharField()
    url = serializers.URLField(required=False, allow_blank=True)
    section = serializers.CharField()
    excerpt = serializers.CharField()
    patent_number = serializers.CharField(required=False, allow_blank=True)


class QueryResponseSerializer(serializers.Serializer):
    """Serializer for query responses."""
    answer = serializers.CharField()
    sources = SourceSerializer(many=True)
    response_time_ms = serializers.IntegerField()


class HealthSerializer(serializers.Serializer):
    """Serializer for health check responses."""
    status = serializers.CharField()
    vector_db_stats = serializers.DictField()
