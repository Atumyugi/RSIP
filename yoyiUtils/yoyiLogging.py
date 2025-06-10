
import sys
import logging

class yoyiLog:
    def __init__(self,logTxt) -> None:
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logTxt,encoding='utf-8'),
            ]
        )
        self.logger = logging.getLogger(__name__)

    def write(self,message):
        if message.rstrip() != "":
            self.logger.info(message.rstrip())
    
    def flush(self):
        pass
        
    

