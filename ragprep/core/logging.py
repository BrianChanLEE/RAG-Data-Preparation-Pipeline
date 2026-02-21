import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger

class ObservabilityFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(ObservabilityFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            from datetime import datetime
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

def setup_observability(run_id: str, log_dir: Path) -> logging.Logger:
    logger = logging.getLogger("ragprep")
    
    if getattr(logger, '_is_setup', False):
        return logger
        
    logger.setLevel(logging.INFO)
    
    log_file = log_dir / f"rag-prepare-{run_id}.log"
    logHandler = logging.FileHandler(log_file)
    formatter = ObservabilityFormatter('%(timestamp)s %(level)s %(name)s %(run_id)s %(doc_id)s %(group_id)s %(stage)s %(event)s %(duration_ms)s %(message)s')
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(streamHandler)
    
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.run_id = run_id
        
        # Add placeholders only if they don't exist yet, 
        # but since makeRecord does not tolerate overwriting,
        # we will let jsonlogger handle missing keys or provide defaults in makeRecord?
        # Actually Python's JsonFormatter handles missing fields gracefully by defaulting to None.
        
        return record
        
    logging.setLogRecordFactory(record_factory)
    logger._is_setup = True
    return logger
