"""
Taiwan Patent scraper service.
Comprehensive scraper using Web Scraper + FTPS Downloader + XML Parser
"""
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional

from django.conf import settings

from .tipo_web_scraper import TIPOWebScraper, scrape_patent_links
from .tipo_ftps_downloader import TIPOFTPSDownloader, download_patent_data_from_links
from .tipo_xml_parser import TIPOXMLParser, parse_patent_directory

logger = logging.getLogger(__name__)


class TaiwanPatentScraper:
    """
    Taiwan Patent Office 完整爬蟲系統
    整合: Web Scraper (爬取下載連結) + FTPS Downloader (下載檔案) + XML Parser (解析資料)
    """

    # Patent categories mapping to TIPO dataset types
    SECTIONS = {
        'invention': 'patent_announce_xml_single',  # 發明專利公告 (1案1XML)
        'utility': 'patent_announce_xml_single',     # 新型專利公告 (1案1XML)
        'design': 'patent_announce_xml_single',      # 設計專利公告 (1案1XML)
        'invention_pub': 'invention_pub_xml_single', # 發明公開 (1案1XML)
        'all': 'patent_announce_xml_single',         # 所有專利
    }

    def __init__(self, max_pages: int = None):
        """
        Initialize the scraper.

        Args:
            max_pages: Maximum number of periods to scrape (affects download size)
        """
        self.max_periods = max_pages or getattr(settings, 'MAX_PAGES_TO_SCRAPE', 5)
        self.web_scraper = TIPOWebScraper(headless=True)
        self.ftps_downloader = TIPOFTPSDownloader()
        self.xml_parser = TIPOXMLParser()

    def scrape_section(
        self,
        section: str,
        latest_only: bool = True,
        xml_only: bool = True,
        max_files_per_period: int = 100
    ) -> List[Dict]:
        """
        完整的專利爬取流程:
        1. 爬取下載連結
        2. 下載 FTPS 檔案
        3. 解析 XML 成專利文件

        Args:
            section: Patent category ('invention', 'utility', 'design', 'all', 'invention_pub')
            latest_only: 是否只爬取最新年份
            xml_only: 是否只下載 XML 檔案
            max_files_per_period: 每期最多下載幾個檔案 (控制資料量)

        Returns:
            List of scraped patent documents (格式見 tipo_xml_parser.py)
        """
        if section not in self.SECTIONS:
            raise ValueError(f"Invalid section: {section}. Choose from {list(self.SECTIONS.keys())}")

        dataset_type = self.SECTIONS[section]

        logger.info(f"========== 開始爬取專利: {section} ==========")
        logger.info(f"資料集類型: {dataset_type}")
        logger.info(f"最多期數: {self.max_periods}")

        # Step 1: 爬取下載連結
        logger.info("\n[Step 1/3] 爬取下載連結...")

        links_file = settings.RAW_DATA_DIR / f'{section}_links.json'

        links_data = scrape_patent_links(
            dataset_type=dataset_type,
            latest_only=latest_only,
            max_periods=self.max_periods,
            output_file=str(links_file)
        )

        if not links_data:
            logger.error("無法取得下載連結")
            return []

        total_periods = sum(len(periods) for periods in links_data.values())
        logger.info(f"✓ 取得 {total_periods} 個期別的下載連結")

        # Step 2: 下載 FTPS 檔案
        logger.info("\n[Step 2/3] 下載 FTPS 檔案...")

        download_dir = settings.RAW_DATA_DIR / f'{section}_downloads'

        download_stats = download_patent_data_from_links(
            links_json_file=str(links_file),
            output_dir=str(download_dir),
            xml_only=xml_only,
            latest_year_only=latest_only,
            max_files_per_period=max_files_per_period
        )

        logger.info(f"✓ 下載完成: {download_stats}")

        # Step 3: 解析 XML
        logger.info("\n[Step 3/3] 解析 XML 檔案...")

        patents = self.xml_parser.parse_directory(
            directory=str(download_dir),
            max_files=None  # 解析所有已下載的檔案
        )

        # 儲存解析結果
        output_json = settings.RAW_DATA_DIR / f'{section}_docs.json'
        self.xml_parser.save_patents_json(patents, str(output_json))

        logger.info(f"\n========== 完成! 共取得 {len(patents)} 個專利文件 ==========")

        return patents
