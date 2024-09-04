import datetime
import math
import os
import sqlite3
from typing import NamedTuple

import pandas as pd
import requests
from PIL import Image

PATH_TO_DB = "/home/kaushik/podcast_collage/podcastAddict.db"

# Connect to the SQLite database
conn = sqlite3.connect(PATH_TO_DB)

# Create a cursor object to execute SQL queries
cursor = conn.cursor()

# Run a select query on the episodes table
query = """
SELECT
    x.name,
    p.name,
    x.url,
    x.playbackDate,
    x.duration_ms,
    COALESCE(b1.url, b2.url) AS img_url
FROM episodes x
INNER JOIN podcasts p
ON x.podcast_id = p._id
LEFT JOIN bitmaps b1
ON x.thumbnail_id = b1._id
LEFT JOIN bitmaps b2
ON p.thumbnail_id = b2._id
WHERE x.playbackDate > 0
"""
cursor.execute(query)

# Fetch all the rows returned by the query
rows = cursor.fetchall()

# Close the cursor and the connection
cursor.close()
conn.close()

for row in rows:
    print(row)


# Define a NamedTuple to store the data
class Episode(NamedTuple):
    episode_name: str
    podcast_name: str
    url: str
    date: datetime.date
    duration: datetime.timedelta
    img_url: str

    @classmethod
    def from_row(cls, row):
        episode_name, podcast_name, url, playback_date, duration_ms, img_url = row
        # Convert playback_date to a human-readable date
        date = datetime.datetime.fromtimestamp(playback_date / 1000).date()
        # Convert duration_ms to a time object
        duration = datetime.timedelta(milliseconds=duration_ms)
        return cls(
            episode_name, podcast_name, url, date, duration, img_url
        )  # Include episode_img_url in the return statement


# Convert the rows into Episode objects
episodes = [Episode.from_row(row) for row in rows]

# Convert the episodes list into a DataFrame
df = pd.DataFrame(episodes, columns=Episode._fields)


def filter_and_group_episodes(start_date, end_date=None):
    # Filter the DataFrame to include only episodes within the date range
    df["date"] = pd.to_datetime(df["date"])  # Convert "date" column to datetime type
    if end_date is None:
        end_date = pd.to_datetime("now")  # Set end_date to current date and time
    else:
        end_date = pd.to_datetime(end_date)  # Convert end_date to datetime type
    filtered_episodes = df.loc[(df["date"] >= start_date) & (df["date"] <= end_date)]

    # Group the episodes by date
    episodes_by_date = filtered_episodes.groupby("date")

    return episodes_by_date


# Example usage:
start_date = pd.to_datetime("2024-08-01")
# end_date = pd.to_datetime("2024-09-30")
end_date = None
episodes_by_date = filter_and_group_episodes(start_date, end_date)

# Iterate over the groups
# Create a directory to store the downloaded images
image_directory = "/home/kaushik/podcast_collage/images"
os.makedirs(image_directory, exist_ok=True)

for date, group in episodes_by_date:
    # Print the date
    print(f"Date: {date.date()}")

    # Remove entries from the group where the img_url column doesn't start with http
    group = group[group["img_url"].str.startswith("http")]

    # If there are no valid img_url entries, skip to the next date
    if group.empty:
        continue

    # Iterate over the episodes for the date
    for _, episode in group.iterrows():
        # Print the podcast name and episode name
        print(f"Podcast: {episode['podcast_name']}, Episode: {episode['episode_name']}")

        # Download the image
        img_url = episode["img_url"]
        image_filename = f"{date.date()}_{episode['episode_name']}.jpg"
        image_path = os.path.join(image_directory, image_filename)
        response = requests.get(img_url)
        with open(image_path, "wb") as f:
            f.write(response.content)

    # Create a blank canvas for the collage
    image_size = 250
    num_images = len(group)
    num_cols = int(math.ceil(math.sqrt(num_images)))
    num_rows = int(math.ceil(num_images / num_cols))
    canvas_width = num_cols * image_size
    canvas_height = num_rows * image_size
    canvas = Image.new("RGB", (canvas_width, canvas_height))

    # Calculate the dimensions for each image in the collage
    image_width = canvas_width // num_cols
    image_height = canvas_height // num_rows

    # Iterate over the episodes for the date
    for i, (_, episode) in enumerate(group.iterrows()):
        # Open the downloaded image
        image_path = os.path.join(
            image_directory, f"{date.date()}_{episode['episode_name']}.jpg"
        )

        image = Image.open(image_path)

        # Resize the image to fit the dimensions
        image = image.resize((image_width, image_height))

        # Calculate the position to paste the image on the canvas
        row = i // num_cols
        col = i % num_cols
        x = col * image_width
        y = row * image_height

        # Paste the image on the canvas
        canvas.paste(image, (x, y))

    # Save the collage
    collage_filename = f"{date.date()}_collage.jpg"
    collage_path = os.path.join(image_directory, collage_filename)
    canvas.save(collage_path)

    # Print the path to the collage
    print(f"Collage saved at: {collage_path}")

    # Print a separator
    print("-" * 20)
