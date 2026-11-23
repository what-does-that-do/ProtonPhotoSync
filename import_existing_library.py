from proton_photo_library import ProtonPhotoLibrary
from mac_photo_library import MacPhotoLibrary

import json
import os
from os import listdir, path, remove
from datetime import datetime, timezone

print("-> Setup Proton Sync with an existing Apple Photo Library.")
print("[i] Existing media is determined based on the creation date.")
SETTINGS = {}

print("[?] Please enter the path to your local photo library.")
SETTINGS["location"] = input()

print("[?] How many days do you want to sync locally to your computer? Enter 0 for infinite.")
SETTINGS["days_ago"] = int(input())

print("[?] What sync interval mins should be used? Default is 2 mins.")
d = input()
if d != "" and d != "0":
    SETTINGS["sync_timeout_mins"] = int(d)
else:
    SETTINGS["sync_timeout_mins"] = 2

with open("settings.json", "w") as s:
    s.write(json.dumps(SETTINGS))

uuid_map_path = path.join(SETTINGS["location"], "uuid_map.json")
temp_path = path.join(SETTINGS["location"], ".temp")
os.makedirs(temp_path, exist_ok=True)

proton = ProtonPhotoLibrary(SETTINGS["location"], download_path=temp_path)
local = MacPhotoLibrary(SETTINGS["location"], export_path=temp_path)

uuid_map = {}
with open(uuid_map_path, "w") as u:
    u.write(json.dumps(uuid_map))

print("Creating Proton delete album...")
proton_delete_album = proton.create_album("to_be_deleted")["uid"]
with open(path.join(SETTINGS["location"], "proton_delete_album.txt"), "w") as p:
    p.write(proton_delete_album)

# clear the temp folder
for file in listdir(temp_path):
    remove(path.join(temp_path, file))

# list all photos on Proton
print("Reading Proton Photos...")
proton_library = proton.get_timeline()
print("Discovered", len(proton_library), "photos on Proton Drive.")

print("Reading Apple library...")
apple_library = local.list_all()
print("Discovered", len(apple_library), "Apple photos. Processing...")

apple_date_uuid_map = {}

duplicate_times = 0
for photo in apple_library:
    apple_date_created = datetime.fromisoformat(photo["date_original"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    print(photo["date_original"],"read as", apple_date_created)
    
    if apple_date_created in apple_date_uuid_map:
        duplicate_times += 1
        apple_date_uuid_map[apple_date_created] = "XX DUPLICATE XX"
    else:
        apple_date_uuid_map[apple_date_created] = photo["uuid"]

print(duplicate_times, "photos exist with duplicated times.")
print("Processed. Now comparing dates with Proton...")

mapped = 0
for photo in proton_library:
    proton_date_created = photo["captureTime"][:-5]
    if proton_date_created in apple_date_uuid_map:
        apple_uuid = apple_date_uuid_map[proton_date_created]

        # ignore the duplicates
        if apple_uuid == "XX DUPLICATE XX":
            continue

        uuid_map[photo["nodeUid"]] = apple_uuid
        mapped += 1

with open(uuid_map_path, "w") as u:
    u.write(json.dumps(uuid_map))

print("Done. Now you can run the regular sync file!")
print("->", len(proton_library), "exist on Proton.")
print("-> Successfully mapped", mapped, "of these photos to local copies.")
print("->", len(apple_library), "total Apple Photos.")

print("[!] Be aware, local copies will be deleted if the date range is less than what is already on your Mac.")
print("e.g. if you set to sync for 2 days, photos more than 3 days old will be deleted from this device but stay on Proton.")