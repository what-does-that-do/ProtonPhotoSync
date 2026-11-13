import os
import subprocess
import re
import json

class MacPhotoLibrary:
    def __init__(self, path: str):
        self.path = path
        # get library file path in directory
        self.library = os.path.join(self.path, [file for file in os.listdir(path) if re.search("\.photoslibrary$", file)][0])

    def get_photo(self, filename: str):
        result = subprocess.run(
            ["osxphotos", "query", "--name", filename, "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)

    def add_photo(self, path: str):
        subprocess.run(
            ["osxphotos", "import", path, "--library", self.library],
            capture_output=True,
            check=True
        )