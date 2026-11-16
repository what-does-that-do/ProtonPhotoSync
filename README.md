# ProtonPhotoSync
Sync photos locally to and from your computer from Proton Drive Photos. Uses the `proton-drive` and `osxphotos` CLIs from a Python script.

## Mac Photos Support
🟡 Partial support. Sync is supported, photos can be downloaded and uploaded between Proton Drive and a Mac Photo library. However, photos need to be manually deleted as this is impossible from the CLI interface.

### Setup
Clone this repository to a memorable location.

#### Mac Setup

Please download the following dependencies (and ensure they are accessible by this script or add them to PATH by copying to `/usr/local/bin`):

Dependency | Link |
---------|----------|
 proton-drive cli | https://proton.me/download/drive/cli/index.html |
 osxphotos cli | https://rhettbull.github.io/osxphotos/overview.html#installation |
 exiftool (for osxphotos) | https://exiftool.org/install.html#MacOS |

Log in to Proton Drive by running `proton-drive auth login`.

Hold option and open Photos. Create a new photo library at your desired location. **It is strongly discouraged to start with an existing library.** Existing libraries will cause photos to be duplicated between Proton Photos and your computer on first sync.

Now copy the directory path containing your photo library (not including the file itself in that path). For example: a library at `/home/user/Desktop/test.photoslibrary` the path entered would be `/home/user/Desktop/`.

Run `python3 sync.py`. On first run, you will be guided through setup, use the directory above when prompted. Now the sync should run automatically!

> Trash does not work with Apple Photos or Proton Drive CLIs. So, photos that would usually have been moved to trash by this script will be placed in an album named `to_be_deleted`. Please select all photos in this album and delete them periodically!

## Windows & Linux
Support is on the way :)

## Automation

Add this script to a crontab, and route the logs to a file - and this can run automatically at login!