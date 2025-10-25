"""
Management command to scrape Taiwan patent data.
"""
from django.core.management.base import BaseCommand
from rag.services.scraper import TaiwanPatentScraper


class Command(BaseCommand):
    help = 'Scrape Taiwan patent data from TIPO (台灣智慧財產局)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--section',
            type=str,
            default='invention',
            choices=['invention', 'utility', 'design', 'invention_pub', 'all'],
            help='Patent section to scrape (invention, utility, design, invention_pub, all). Default: invention'
        )
        parser.add_argument(
            '--max-periods',
            type=int,
            default=5,
            help='Maximum number of periods to scrape (affects download size). Default: 5'
        )
        parser.add_argument(
            '--latest-only',
            action='store_true',
            help='Only scrape the latest year'
        )
        parser.add_argument(
            '--max-files-per-period',
            type=int,
            default=100,
            help='Maximum number of files to download per period. Default: 100'
        )

    def handle(self, *args, **options):
        section = options['section']
        max_periods = options['max_periods']
        latest_only = options['latest_only']
        max_files_per_period = options['max_files_per_period']

        self.stdout.write(self.style.SUCCESS('開始爬取台灣專利資料...'))
        self.stdout.write(f'專利類別: {section}')
        self.stdout.write(f'最多期數: {max_periods}')
        self.stdout.write(f'只爬取最新年份: {"是" if latest_only else "否"}')
        self.stdout.write(f'每期最多檔案數: {max_files_per_period}')

        scraper = TaiwanPatentScraper(max_pages=max_periods)

        try:
            patents = scraper.scrape_section(
                section=section,
                latest_only=latest_only,
                xml_only=True,
                max_files_per_period=max_files_per_period
            )

            self.stdout.write(
                self.style.SUCCESS(f'✓ 成功爬取 {len(patents)} 個專利文件')
            )

            # Display sample patent info
            if patents:
                self.stdout.write(self.style.SUCCESS('\n範例專利資訊:'))
                sample = patents[0]
                self.stdout.write(f'  專利號: {sample.get("patent_number", "N/A")}')
                self.stdout.write(f'  專利名稱: {sample.get("title", "N/A")}')
                self.stdout.write(f'  申請人: {sample.get("applicant", "N/A")}')
                self.stdout.write(f'  IPC分類: {sample.get("ipc_classification", "N/A")}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'爬取失敗: {e}')
            )
            raise
