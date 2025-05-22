import json
import os
import logging
from datetime import datetime
import schedule
import threading
import time
import requests

logger = logging.getLogger('xml_downloader_module')

class XMLDownloaderModule:
    CONFIG_FILE = os.path.join('data', 'xml_config.json')
    DEFAULT_XML_PATH = os.path.join('data', 'products_latest.xml')
    
    def __init__(self):
        self.config = self.load_config()
        self.scheduler_thread = None
        self.stop_scheduler_event = threading.Event()

    def load_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    # Ensure all expected keys are present
                    default_config = {'url': 'https://ergo.enode.ovh/products.xml', 'interval_minutes': 10, 'auto_start': True, 'last_download': 'N/A', 'download_on_start': True}
                    default_config.update(loaded_config)
                    return default_config
        except Exception as e:
            logger.error(f"Error loading XML config: {e}")
        return {'url': 'https://ergo.enode.ovh/products.xml', 'interval_minutes': 10, 'auto_start': True, 'last_download': 'N/A', 'download_on_start': True}

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("XML config saved.")
        except Exception as e:
            logger.error(f"Error saving XML config: {e}")

    def update_config(self, new_url, new_interval_minutes, auto_start):
        self.config['url'] = new_url
        self.config['interval_minutes'] = int(new_interval_minutes)
        self.config['auto_start'] = auto_start
        self.save_config()
        logger.info(f"XML config updated: URL={new_url}, Interval={new_interval_minutes}min, AutoStart={auto_start}")
        
        # Stop current scheduler if running
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.stop_scheduler()
        
        # Restart scheduler if auto_start is true
        if auto_start:
            self.start_scheduler()
        return self.config

    def download_xml_file(self):
        url = self.config.get('url')
        if not url:
            logger.error("XML URL not configured.")
            return False
        
        xml_dir = os.path.dirname(self.DEFAULT_XML_PATH)
        os.makedirs(xml_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = os.path.join(xml_dir, f"products_{timestamp}.xml")
        
        try:
            logger.info(f"Attempting to download XML from {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(archive_filename, 'wb') as f:
                f.write(response.content)
            logger.info(f"XML downloaded and saved to {archive_filename}")

            with open(self.DEFAULT_XML_PATH, 'wb') as f:
                f.write(response.content)
            logger.info(f"XML saved as latest to {self.DEFAULT_XML_PATH}")
            
            self.config['last_download'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.save_config()
            self.cleanup_old_files(xml_dir)
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading XML: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during XML download: {e}")
        return False

    def cleanup_old_files(self, directory, keep_last=24):
        try:
            files = [os.path.join(directory, f) for f in os.listdir(directory) 
                     if f.startswith("products_") and f.endswith(".xml") and not f == os.path.basename(self.DEFAULT_XML_PATH)]
            files.sort(key=lambda x: os.path.getmtime(x))
            
            for old_file in files[:-keep_last]:
                os.remove(old_file)
                logger.info(f"Removed old XML file: {old_file}")
        except Exception as e:
            logger.error(f"Error cleaning up old XML files: {e}")

    def _scheduler_loop(self):
        interval = self.config.get('interval_minutes', 10)
        logger.info(f"Scheduler started. Interval: {interval} minutes.")
        
        # Initial download if configured
        if self.config.get('download_on_start', True):
             logger.info("Performing initial XML download on start.")
             self.download_xml_file()

        # Clear any existing jobs before scheduling a new one
        schedule.clear()
        schedule.every(interval).minutes.do(self.download_xml_file)

        while not self.stop_scheduler_event.is_set():
            schedule.run_pending()
            time.sleep(1) # Check every second
        
        logger.info("Scheduler loop stopped.")
        schedule.clear() # Clear schedules when stopping


    def start_scheduler(self):
        if self.config.get('auto_start', False):
            if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
                self.stop_scheduler_event.clear()
                self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
                self.scheduler_thread.start()
                logger.info("XML Download scheduler thread started.")
            else:
                logger.info("Scheduler already running.")
        else:
            logger.info("Auto-start for XML scheduler is disabled in config.")

    def stop_scheduler(self):
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.info("Attempting to stop scheduler thread...")
            self.stop_scheduler_event.set()
            self.scheduler_thread.join(timeout=5) 
            if self.scheduler_thread.is_alive():
                logger.warning("Scheduler thread did not stop gracefully.")
            else:
                logger.info("XML Download scheduler thread stopped.")
            self.scheduler_thread = None
        else:
            logger.info("Scheduler not running or already stopped.")

    def get_status(self):
        return {
            'running': self.scheduler_thread is not None and self.scheduler_thread.is_alive(),
            'config': self.config,
            'next_run': str(schedule.next_run()) if schedule.jobs else 'Not scheduled'
        }

# Global instance
xml_downloader_instance = XMLDownloaderModule() # Renamed for clarity

def initialize_xml_downloader():
    logger.info("Initializing XML Downloader Module...")
    xml_downloader_instance.start_scheduler()

def get_xml_downloader_instance():
    return xml_downloader_instance
