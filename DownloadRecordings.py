from pytapo import Tapo
from pytapo.media_stream.downloader import Downloader
import asyncio
import os
import datetime

# mandatory
output_dir = os.environ.get("OUTPUT")  # directory path where videos will be saved
start_datetime = os.environ.get("START_DATETIME")  # start date in format YYYY-MM-DDTHH:MM:SS
end_datetime = os.environ.get("END_DATETIME")  # end date in format YYYY-MM-DDTHH:MM:SS
host = os.environ.get("HOST")  # change to camera IP
password_cloud = os.environ.get("PASSWORD_CLOUD")  # set to your cloud password

# optional
window_size = os.environ.get(
    "WINDOW_SIZE"
)  # set to prefferred window size, affects download speed and stability, recommended: 50

print("Connecting to camera...")
tapo = Tapo(host, "admin", password_cloud, password_cloud)


async def download_async():
    global output_dir, start_datetime, end_datetime, window_size
    print("Getting recordings...")
    if not output_dir or not os.path.exists(output_dir) or not os.path.isdir(output_dir):
        exit("ERROR: OUTPUT must be set and directory must exist")

    if output_dir[-1] != "/":
        output_dir = output_dir + "/"

    if start_datetime is None or len(start_datetime) == 0:
        exit("ERROR: START_DATETIME must be set")
    if end_datetime is None or len(end_datetime) == 0:
        exit("ERROR: END_DATETIME must be set")

    # parse start and end dates into datetime objects
    start = datetime.datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S")
    end = datetime.datetime.strptime(end_datetime, "%Y-%m-%dT%H:%M:%S")
    # format date to get YYYYMMDD string
    date = start.strftime("%Y%m%d")
    while end <= start:
        exit("ERROR: End date cannot be before start date")

    if window_size is None or len(window_size) == 0:
        print("Using default window size: 50 seconds")
        window_size = 50
    
    recordings = tapo.getRecordings(date)
    timeCorrection = tapo.getTimeCorrection()
    for recording in recordings:
        for key in recording:
            # parse unix epoch
            startTime = datetime.datetime.fromtimestamp(int(recording[key]["startTime"]))
            endTime = datetime.datetime.fromtimestamp(int(recording[key]["endTime"]))
            if startTime > end or endTime < start:
                print(f'Skipping recording: {key}, out of time range, is {startTime} - {endTime}')
                continue
 
            downloader = Downloader(
                tapo,
                recording[key]["startTime"],
                recording[key]["endTime"],
                timeCorrection,
                output_dir,
                None,
                False,
                window_size,
            )
            async for status in downloader.download():
                statusString = status["currentAction"] + " " + status["fileName"]
                if status["progress"] > 0:
                    statusString += (
                        ": "
                        + str(round(status["progress"], 2))
                        + " / "
                        + str(status["total"])
                    )
                else:
                    statusString += "..."
                print(
                    statusString + (" " * 10) + "\r",
                    end="",
                )
            print("")


loop = asyncio.get_event_loop()
loop.run_until_complete(download_async())
