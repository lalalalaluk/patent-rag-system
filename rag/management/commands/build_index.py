"""
Management command to build the vector database index.
"""
from django.core.management.base import BaseCommand
from rag.services.rag_engine import RAGEngine


class Command(BaseCommand):
    help = 'Build vector database index from processed documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sections',
            nargs='+',
            type=str,
            default=None,
            help='Sections to index. Default: all available'
        )
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild index from scratch (delete existing data)'
        )

    def handle(self, *args, **options):
        sections = options['sections']

        self.stdout.write(self.style.SUCCESS('Starting index build...'))

        if options['rebuild']:
            self.stdout.write(self.style.WARNING('Rebuilding index from scratch'))

        rag_engine = RAGEngine()

        try:
            rag_engine.index_documents(sections=sections)

            stats = rag_engine.get_stats()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully indexed {stats["total_documents"]} documents'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error building index: {e}')
            )
            raise
