"""
Management command to test a query.
"""
from django.core.management.base import BaseCommand
from rag.services.rag_engine import RAGEngine


class Command(BaseCommand):
    help = 'Test a query against the RAG system'

    def add_arguments(self, parser):
        parser.add_argument(
            'question',
            type=str,
            help='Question to ask'
        )

    def handle(self, *args, **options):
        question = options['question']

        self.stdout.write(self.style.SUCCESS(f'Query: {question}'))
        self.stdout.write('-' * 80)

        rag_engine = RAGEngine()

        try:
            result = rag_engine.query(question)

            self.stdout.write(self.style.SUCCESS('\nAnswer:'))
            self.stdout.write(result['answer'])

            self.stdout.write('\n' + '-' * 80)
            self.stdout.write(self.style.SUCCESS('\nSources:'))
            if result['sources']:
                for i, source in enumerate(result['sources'], 1):
                    self.stdout.write(f"\n[{i}] {source['title']}")
                    self.stdout.write(f"    Patent Number: {source.get('patent_number', 'N/A')}")
                    self.stdout.write(f"    Applicant: {source.get('applicant', 'N/A')}")
                    self.stdout.write(f"    IPC: {source.get('ipc_classification', 'N/A')}")
                    self.stdout.write(f"    Section: {source['section']}")
            else:
                self.stdout.write("\n(No relevant patents found)")

            self.stdout.write('\n' + '-' * 80)
            self.stdout.write(
                f"Response time: {result['response_time_ms']}ms"
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing query: {e}')
            )
            raise
