import os
import subprocess
import re
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class MacPhotoLibrary:
    def __init__(self, path: str, export_path: str):
        self.path = path
        self.uuids = []
        self.export_path = export_path
        # get library file path in directory
        self.library = os.path.join(self.path, [file for file in os.listdir(path) if re.search("\.photoslibrary$", file)][0])

    def search_filename(self, filename: str):
        command = ["osxphotos", "query", "--name", filename, "--json"]
        logging.debug("%s", command)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)

    def list_all(self):
        command = ["osxphotos", "query", "--query-eval", "'to_be_deleted' not in photo.albums", "--json"]
        logging.debug("%s", command)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        l = json.loads(result.stdout)
        self.uuids = self.format_to_uuid_list(l)
        return l

    def add_photo(self, path: str, return_uuid: bool = True) -> str:
        """Adds a photo to Apple Photo library.

        Args:
            path (str): Filepath of the photo.
            return_uuid (bool, optional): Whether to return UUID or not.

        Returns:
            str: UUID created for the photo
        """
        command = ["osxphotos", "import", path, "--library", self.library]
        logging.debug("%s", command)
        result = subprocess.run(
            command,
            capture_output=True,
            check=True
        )
        return self.search_filename(path.split("/")[-1])[0]["uuid"]

    def export_photo(self, uuid: str):
        command = ["osxphotos", "export", self.export_path, "--uuid", uuid ,"--exiftool", "--library", self.library]
        logging.debug("%s", command)
        result = subprocess.run(
                    command,
                    capture_output=True,
                    check=True
                )

    def add_to_album(self, uuid, album_name):
        command = ["osxphotos", "query", "--uuid", uuid, "--add-to-album", album_name]
        logging.debug("%s", command)
        result = subprocess.run(
                    command,
                    capture_output=True,
                    check=True
                )
    
    def format_to_uuid_list(self, timeline):
        uuids = []

        for photo in timeline:
            uuids.append(photo["uuid"])

        return uuids