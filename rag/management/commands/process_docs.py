"""
Management command to process scraped documents into chunks.
"""
from django.core.management.base import BaseCommand
from rag.services.document_processor import DocumentProcessor


class Command(BaseCommand):
    help = 'Process scraped documents into chunks for embedding'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sections',
            nargs='+',
            type=str,
            default=None,
            help='Sections to process. Default: all available'
        )

    def handle(self, *args, **options):
        sections = options['sections']

        self.stdout.write(self.style.SUCCESS('Starting document processing...'))

        processor = DocumentProcessor()

        try:
            all_processed = processor.process_all_sections(sections=sections)

            total_chunks = sum(len(chunks) for chunks in all_processed.values())
            self.stdout.write(
                self.style.SUCCESS(f'Successfully processed {total_chunks} chunks')
            )

            for section, chunks in all_processed.items():
                stats = processor.get_chunk_statistics(chunks)
                self.stdout.write(f'  - {section}: {len(chunks)} chunks')
                self.stdout.write(
                    f'    Avg length: {stats["avg_chunk_length"]:.0f} chars'
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during processing: {e}')
            )
            raise
