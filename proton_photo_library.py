import subprocess
import json
import re
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class ProtonPhotoLibrary:
    def __init__(self, path: str, download_path: str):
        self.path = path
        self.uuids = []
        self.download_path = download_path
    
    def authenticate(self):
        command = ["proton-drive", "auth", "login"]
        logging.debug("%s", command)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

    def get_timeline(self, total_days_ago: int = 0):
        command = ["proton-drive", "photo", "timeline", "-j"]
        logging.debug("%s", command)
        command_result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        result = json.loads(command_result.stdout)

        if total_days_ago > 0:
            out = self.filter_timeline(result, total_days_ago)
        else:
            out = result
        
        self.uuids = self.format_to_uuid_list(out)
        return out

    def filter_timeline(self, timeline: list[dict], total_days_ago: int):
        timeline_result = []
        # get date of x days ago
        earliest_date = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=total_days_ago)
        logging.info("Photos must be after %s", earliest_date.strftime("%Y-%m-%d"))

        # get all photos that match criteria
        for photo in timeline:
            if datetime.fromisoformat(photo["captureTime"]) > earliest_date:
                timeline_result.append(photo)

        return timeline_result

    def download_photo(self, uuid: str):
        command = ["proton-drive", "photo", "download", "/photos/"+uuid+"", self.download_path, "-j"]
        logging.debug("%s", command)
        result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True
                )

    def upload_photo(self, photo_path: str):
        command = ["proton-drive", "photo", "upload", photo_path, "--json", "--verbose"]
        logging.debug("%s", command)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # UUID must be read from the verbose logs.
        # Read stdout verbose line by line as the process runs
        uuid = None
        for line in process.stdout:
            # Search for the UUID in the log line
            if "upload succeeded" in line.lower().strip():
                uuid = line.split("INFO [upload] revision ")[1].split(":")[0]
                uuid = uuid[:45]
        
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError(f"Proton Drive upload failed with code {process.returncode}")

        logging.info("Successfully uploaded with uuid: %s", uuid)
        return uuid

    def add_to_album(self, uuid, album_uid):
        command = ["proton-drive", "album", "add-photo", "/albums/"+album_uid, "/photos/"+uuid, "-j"]
        logging.debug("%s", command)
        result = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            check=True
                        )

    def list_albums(self):
        command = ["proton-drive", "album", "list"]
        logging.debug("%s", command)
        result = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            check=True
                        )

        return json.loads(result.stdout)

    def get_album(self, uid):
        command = ["proton-drive", "album", "photos", "/albums/"+uid, "-j"]
        logging.debug("%s", command)
        result = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            check=True
                        )

        return json.loads(result.stdout)

    def create_album(self, name):
        command = ["proton-drive", "album", "create", name, "-j"]
        logging.debug("%s", command)
        result = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            check=True
                        )

        return json.loads(result.stdout)

    def format_to_uuid_list(self, timeline):
        uuids = []

        for photo in timeline:
            uuids.append(photo["nodeUid"])

        return uuids