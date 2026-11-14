from os import listdir, path, mkdir, remove
from datetime import datetime, timedelta, timezone

from time import sleep
import threading
from proton_photo_library import *
from mac_photo_library import *

# use 0 days ago for infinite sync
SETTINGS = {
    "location": "test",
    "days_ago": 5
}

proton = ProtonPhotoLibrary(SETTINGS["location"])
mac = MacPhotoLibrary(SETTINGS["location"])
uuid_map_path = path.join(SETTINGS["location"], "uuid_map.json")
temp_path = path.join(SETTINGS["location"], ".temp")

def save_to_mac(photo, filename):
    print("Adding photo...")
    mac_uuid = mac.add_photo(path.join(temp_path, filename))
    uuid_map[photo["nodeUid"]] = mac_uuid
    remove(path.join(temp_path, filename))

    print("Done.")

def download_proton(timeline):
    print("Photos on Proton Drive:", len(timeline))
    download_queue = []

    # get all photos after date
    if SETTINGS["days_ago"] > 0:
        earliest_date = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=SETTINGS["days_ago"])

        for photo in timeline:
            if datetime.fromisoformat(photo["captureTime"]) > earliest_date:
                download_queue.append(photo)
    else:
        download_queue = timeline

    print("To download from Proton:", len(download_queue))

    # clear temp directory first
    if not path.exists(temp_path):
        mkdir(temp_path)
    else:
        for item in listdir(temp_path):
            remove(path.join(temp_path, item))

    n = 0
    mac_thread = None
    for photo in download_queue:
        n += 1
        print("Downloading photo", n, "of", len(download_queue))
        proton.download_photo(photo["nodeUid"], temp_path)
        filename = listdir(temp_path)[0]

        if mac_thread != None:
            while mac_thread.is_alive():
                print("Waiting for prev. photo to be imported.")
                sleep(1)
                
        mac_thread = threading.Thread(target=save_to_mac, args=(photo, filename,))
        mac_thread.start()

    with open(uuid_map_path, "w") as u:
        u.write(json.dumps(uuid_map))
    print("Finished.")

print("Reading Proton Photos...")
timeline = proton.get_timeline(dev=True)

# if the map between proton and mac doesn't exist, treat as new library
if not path.exists(uuid_map_path):
    print("Treating as new sync setup.")
    uuid_map = {}
    with open(uuid_map_path, "w") as u:
        u.write(json.dumps(uuid_map))
else:
    print("Existing sync setup.")
    with open(uuid_map_path, "w") as u:
        uuid_map = json.loads(u.read())

download_proton(timeline)