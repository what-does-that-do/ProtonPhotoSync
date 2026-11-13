import subprocess
import json

class ProtonPhotoLibrary:
    def __init__(self, path: str):
        self.path = path

    def authenticate(self):
        subprocess.run(
            ["proton-drive", "auth", "login"], 
            check=True
        )

    def get_timeline(self, dev=False):
        if dev:
            with open("out.json", "rb") as p:
                return json.loads(p.read())

        result = subprocess.run(
            ["proton-drive", "photo", "timeline", "-j"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)

    def download_photo(self, uuid: str, out_path: str):
        result = subprocess.run(
                    ["proton-drive", "photo", "download", "/photos/"+uuid+"", out_path, "-j"],
                    stdout=subprocess.DEVNULL,
                    text=True,
                    check=True
                )