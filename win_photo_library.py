import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

'''
Windows Implementation of the Mac Photo Library.
Photos are placed into a specified directory, then synced to there.
A UUID is generated for each local file to track changes.

Created with the help of AI, using a prompt to adjust the Mac library.
'''

class WinPhotoLibrary:
    def __init__(self, path: str, export_path: str):
        self.path = path
        self.local_map = os.path.join(self.path, "local_map.json")
        self.photos_path = os.path.join(self.path, "Photos")
        self.uuids: list[str] = []
        self.filenames: list[str] = []
        self.export_path = export_path
        os.makedirs(self.photos_path, exist_ok=True)

    def get_local_file_map(self) -> dict[str, str]:
        if not os.path.exists(self.local_map):
            return {}

        with open(self.local_map, "r", encoding="utf-8") as file:
            file_map = json.load(file)
        
        if not isinstance(file_map, dict) or not all(
            isinstance(file_uuid, str)
            and isinstance(filename, str)
            and os.path.basename(filename) == filename
            for file_uuid, filename in file_map.items()
        ):
            raise ValueError(f"Invalid photo map in {self.local_map}")
        return file_map

    def save_local_file_map(self, file_map: dict[str, str]) -> None:
        with open(self.local_map, "w", encoding="utf-8") as file:
            json.dump(file_map, file)

    def _index_unmapped_files(self) -> dict[str, str]:
        file_map = self.get_local_file_map()
        available_files = {
            os.path.normcase(filename): filename
            for filename in os.listdir(self.photos_path)
            if os.path.isfile(os.path.join(self.photos_path, filename))
        }
        # Drop mappings for removed files and assign UUIDs to files added outside this class.
        file_map = {
            file_uuid: filename
            for file_uuid, filename in file_map.items()
            if os.path.normcase(filename) in available_files
        }
        mapped_filenames = {
            os.path.normcase(filename) for filename in file_map.values()
        }

        for filename in sorted(available_files.values()):
            if os.path.normcase(filename) in mapped_filenames:
                continue

            file_uuid = str(uuid.uuid4())
            file_map[file_uuid] = filename
            mapped_filenames.add(os.path.normcase(filename))

        self.save_local_file_map(file_map)
        return file_map

    def _photo_path(self, file_uuid: str) -> str:
        file_map = self.get_local_file_map()
        if file_uuid not in file_map:
            raise KeyError(f"Photo UUID not found: {file_uuid}")

        filename = file_map[file_uuid]
        if os.path.basename(filename) != filename:
            raise ValueError(f"Invalid filename for photo UUID {file_uuid}")

        file_path = os.path.join(self.photos_path, filename)
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Photo file not found for UUID {file_uuid}")
        return file_path

    def _photo_record(self, file_uuid: str, filename: str) -> dict[str, str]:
        file_path = os.path.join(self.photos_path, filename)
        date_original = datetime.fromtimestamp(
            os.path.getmtime(file_path), tz=timezone.utc
        ).isoformat()
        return {
            "uuid": file_uuid,
            "filename": filename,
            "date_original": date_original,
        }

    def search_filename(self, filename: str) -> list[dict[str, str]]:
        file_map = self._index_unmapped_files()
        target_filename = os.path.basename(filename).casefold()
        return [
            self._photo_record(file_uuid, photo_filename)
            for file_uuid, photo_filename in file_map.items()
            if photo_filename.casefold() == target_filename
            and os.path.isfile(os.path.join(self.photos_path, photo_filename))
        ]

    def list_all(self) -> list[dict[str, str]]:
        file_map = self._index_unmapped_files()
        output = [
            self._photo_record(file_uuid, filename)
            for file_uuid, filename in file_map.items()
            if os.path.isfile(os.path.join(self.photos_path, filename))
        ]
        self.uuids = self.format_to_uuid_list(output)
        return output

    def add_photo(self, path: str, return_uuid: bool = True) -> str:
        """Copy a photo into the local library and return its stable UUID."""
        source_path = os.path.abspath(path)
        if not os.path.isfile(source_path):
            raise FileNotFoundError(f"Photo file not found: {path}")

        library_path = os.path.abspath(self.photos_path)
        try:
            source_is_in_library = os.path.normcase(
                os.path.commonpath([source_path, library_path])
            ) == os.path.normcase(library_path)
        except ValueError:
            source_is_in_library = False

        if source_is_in_library:
            file_map = self._index_unmapped_files()
            for file_uuid, filename in file_map.items():
                mapped_path = os.path.normcase(os.path.join(library_path, filename))
                if mapped_path == os.path.normcase(source_path):
                    return file_uuid

        file_uuid = str(uuid.uuid4())
        filename = os.path.basename(source_path)
        name, extension = os.path.splitext(filename)
        destination = os.path.join(self.photos_path, filename)
        if os.path.exists(destination):
            filename = f"{name}_{file_uuid[:8]}{extension}"
            destination = os.path.join(self.photos_path, filename)

        shutil.copy2(source_path, destination)
        file_map = self.get_local_file_map()
        file_map[file_uuid] = filename
        self.save_local_file_map(file_map)
        return file_uuid

    def export_photo(self, uuid: str) -> None:
        source_path = self._photo_path(uuid)
        os.makedirs(self.export_path, exist_ok=True)
        destination = os.path.join(self.export_path, os.path.basename(source_path))
        if os.path.normcase(os.path.abspath(source_path)) != os.path.normcase(
            os.path.abspath(destination)
        ):
            shutil.copy2(source_path, destination)

    def delete_photo(self, uuid: str) -> None:
        photo_path = self._photo_path(uuid)
        os.remove(photo_path)

        file_map = self.get_local_file_map()
        del file_map[uuid]
        self.save_local_file_map(file_map)
        self.uuids = [file_uuid for file_uuid in self.uuids if file_uuid != uuid]

    def format_to_uuid_list(self, timeline: list[dict[str, str]]) -> list[str]:
        return [photo["uuid"] for photo in timeline]

    def format_to_filename_list(self, timeline: list[dict[str, str]]) -> list[str]:
        return [photo["filename"] for photo in timeline]
