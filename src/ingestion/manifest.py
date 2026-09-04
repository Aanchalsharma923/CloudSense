import json
import os
from typing import List, Optional
from src.ingestion.models import ManifestEntry

class ManifestManager:
    def __init__(self, manifest_path: str = "data/raw/manifest.json"):
        self.manifest_path = manifest_path
        self._ensure_exists()
        
    def _ensure_exists(self):
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        if not os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'w') as f:
                json.dump([], f)
                
    def read_manifest(self) -> List[ManifestEntry]:
        with open(self.manifest_path, 'r') as f:
            data = json.load(f)
        return [ManifestEntry(**item) for item in data]
        
    def write_manifest(self, entries: List[ManifestEntry]):
        with open(self.manifest_path, 'w') as f:
            json.dump([e.model_dump() for e in entries], f, indent=2)
            
    def add_entry(self, entry: ManifestEntry):
        entries = self.read_manifest()
        
        # If entry for same dataset, date, and source exists, update it or handle?
        # Typically we want an append-only log, but for idempotency we can just append and pick latest.
        # Let's replace if it's the exact same dataset and observation date and it was fully PROCESSED.
        # Actually, let's just append everything for a complete audit trail.
        entries.append(entry)
        self.write_manifest(entries)
        
    def get_latest_successful(self, dataset: str, observation_date: str) -> Optional[ManifestEntry]:
        entries = self.read_manifest()
        valid = [e for e in entries if e.dataset == dataset and e.observation_date == observation_date and e.processing_status == "PROCESSED"]
        if valid:
            return valid[-1]
        return None

