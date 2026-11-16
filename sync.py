from os import listdir, path, mkdir, remove
from datetime import datetime, timedelta, timezone
import logging

from time import sleep
import threading
from proton_photo_library import *
from mac_photo_library import *

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if "settings.json" not in listdir():
    SETTINGS = {}

    print("-> Welcome to Proton Photo sync!")
    print("[?] Please enter the path to your new Apple Photo Library directory.")
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
else:
    with open("settings.json", "r") as s:
        SETTINGS = json.loads(s.read())

uuid_map_path = path.join(SETTINGS["location"], "uuid_map.json")
temp_path = path.join(SETTINGS["location"], ".temp")

# setup Proton and Mac library connections
proton = ProtonPhotoLibrary(SETTINGS["location"], download_path=temp_path)
mac = MacPhotoLibrary(SETTINGS["location"], export_path=temp_path)

# get uuid map
if not path.exists(uuid_map_path):
    logging.info("New sync setup")
    uuid_map = {}
    with open(uuid_map_path, "w") as u:
        u.write(json.dumps(uuid_map))

    logging.info("Creating Proton delete album...")
    with open(path.join(SETTINGS["location"], "proton_delete_album.txt"), "w") as p:
        p.write(proton.create_album("to_be_deleted")["uid"])
else:
    logging.info("Existing sync setup.")
    with open(uuid_map_path, "r") as u:
        uuid_map = json.loads(u.read())
    
    with open(path.join(SETTINGS["location"], "proton_delete_album.txt"), "r") as p:
        proton_delete_album = p.read()

# clear the temp folder
for file in listdir(temp_path):
    remove(path.join(temp_path, file))

while True:
    # list all photos on Proton
    logging.info("Reading Proton Photos...")
    proton_library = proton.get_timeline(total_days_ago=SETTINGS["days_ago"])
    logging.info(
        "Discovered %s photos after %s days ago on Proton Drive.",
        len(proton_library),
        SETTINGS["days_ago"],
    )

    logging.info("Reading Proton Photos to be deleted album...")
    ignored_proton_uids = []
    to_be_deleted = proton.get_album(proton_delete_album)
    for photo in to_be_deleted:
        ignored_proton_uids.append(photo["nodeUid"])

    logging.info("Reading Apple photo library...")
    apple_library = mac.list_all()
    logging.info("Discovered %s photos in Apple photo library.", len(apple_library))

    for proton_photo in proton.uuids:
        # these photos are to be deleted on proton
        if proton_photo in ignored_proton_uids:
            continue

        # Proton photo is seen by uuid map
        if proton_photo in uuid_map:
            # check equivalent mac uuid still exists
            # NO CHANGE
            if uuid_map[proton_photo] in mac.uuids:
                continue
            # photo no longer local, but is on Proton
            # DELETE from proton
            else:

                logging.info(
                    "Photo with UUID %s needs to be deleted from Proton. Added to album 'to_be_deleted'",
                    proton_photo,
                )
                proton.add_to_album(proton_photo, proton_delete_album)
                uuid_map.pop(proton_photo)
                ignored_proton_uids.append(proton_photo)

                with open(path.join(SETTINGS["location"], "ignored_proton_uids.json"), "w") as u:
                    u.write(json.dumps(ignored_proton_uids))
        else:
            # On Proton, not in the map (never seen before)
            # DOWNLOAD from proton
            logging.info("Downloading photo %s", proton_photo)
            proton.download_photo(proton_photo)

            filename = listdir(temp_path)[0]
            
            logging.info("Adding photo %s to Mac library.", filename)
            mac_uuid = mac.add_photo(path.join(temp_path, filename))
            
            uuid_map[proton_photo] = mac_uuid
            remove(path.join(temp_path, filename))

            # clear the temp folder
            for file in listdir(temp_path):
                remove(path.join(temp_path, file))

        # save state
        with open(uuid_map_path, "w") as u:
            u.write(json.dumps(uuid_map))

    for mac_photo in mac.uuids:
        if mac_photo in uuid_map.values():
            proton_uuid = list(uuid_map.keys())[list(uuid_map.values()).index(mac_photo)]
            # check doesn't exist on proton drive
            # find key by values (treat as 2 lists)
            # NO CHANGE
            if proton_uuid in proton.uuids:
                continue
            # not on Proton, we've seen this before.
            # DELETE from local
            else:                
                uuid_map.pop(proton_uuid)
                mac.add_to_album(mac_photo, "to_be_deleted")
                logging.info(
                    'Photo with UUID %s needs to be deleted from Apple Photos. Added to album "to_be_deleted"',
                    mac_photo,
                )
            
        # only local, not on remote, not seen before
        # UPLOAD to Proton
        else:
            logging.info("Uploading photo %s to Proton Drive...", mac_photo)
            # extract photo from Mac library
            mac.export_photo(mac_photo)
            remove(path.join(temp_path, ".osxphotos_export.db"))

            # upload this to proton
            filename = listdir(temp_path)[0]
            proton_uuid = proton.upload_photo(path.join(temp_path, filename))

            if not proton_uuid:
                logging.error("Error uploading photo: %s", mac_photo)
                continue

            uuid_map[proton_uuid] = mac_photo

            # clear the temp folder
            for file in listdir(temp_path):
                remove(path.join(temp_path, file))

        # save state
        with open(uuid_map_path, "w") as u:
            u.write(json.dumps(uuid_map))

    logging.info("Checking local photo dates...")
    earliest_date = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=SETTINGS["days_ago"])
    for photo in apple_library:
        # delete if older and never seen before
        # (if seen before, it will be uploaded now and deleted on next sync)
        if (datetime.fromisoformat(photo["date_original"]) <= earliest_date) and (photo["uuid"] in uuid_map.values()):
            proton_uuid = list(uuid_map.keys())[list(uuid_map.values()).index(photo["uuid"])]
            uuid_map.pop(proton_uuid)

            mac.add_to_album(photo["uuid"], "to_be_deleted")
            logging.info(
                'Photo with UUID %s needs to be deleted from Apple Photos. Added to album "to_be_deleted"',
                photo["uuid"],
            )

    with open(uuid_map_path, "w") as u:
        u.write(json.dumps(uuid_map))

    logging.info(
        "Sync complete. Waiting %s mins.", SETTINGS["sync_timeout_mins"]
    )
    sleep(SETTINGS["sync_timeout_mins"] * 60)