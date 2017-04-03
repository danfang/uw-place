import math
import sys
import time
import random 
import requests
import base64

from io import BytesIO
from PIL import Image
from requests.adapters import HTTPAdapter

UW_LOGO = """iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAIAAAAC64paAAAAhElEQVR4nGNckOXEQC5gYWBg
             eDTNjgydclmHmMi2loGBYeA0s8BZtf/rkSWaGRshIs2MjciyEC4VbEZoRjYSmY0sgiaO02a4
             OyEMNE9h0YxpIX5ZfH7GbxZOzWiOxOpmAjYTBOia4U5FczNWL7BgCuGPM3w2kwSGqGYWBgYG
             uaxD5GkGAJB3JOlpuqlXAAAAAElFTkSuQmCC"""

ORIGIN = (890, 850)
 
def login(username, password):
    s = requests.Session()
    s.mount('https://www.reddit.com', HTTPAdapter(max_retries=5))
    s.headers["User-Agent"] = "PlacePlacer"
    r = s.post("https://www.reddit.com/api/login/{}".format(username),
               data={"user": username, "passwd": password, "api_type": "json"})

    if r.status_code != 200:
        return None, "HTTP status " + r.status_code

    json = r.json()["json"]

    if len(json["errors"]) > 0:
        return None, json["errors"][0][1]

    s.headers['x-modhash'] = json["data"]["modhash"]
    return s, None
 
def find_palette(point):
    rgb_code_dictionary = {
        (255, 255, 255): 0,
        (228, 228, 228): 1,
        (136, 136, 136): 2,
        (34, 34, 34): 3,
        (255, 167, 209): 4,
        (229, 0, 0): 5,
        (229, 149, 0): 6,
        (160, 106, 66): 7,
        (229, 217, 0): 8,
        (148, 224, 68): 9,
        (2, 190, 1): 10,
        (0, 211, 211): 11,
        (0, 131, 199): 12,
        (0, 0, 234): 13,
        (207, 110, 228): 14,
        (130, 0, 128): 15
    }
 
    def distance(c1, c2):
        (r1, g1, b1) = c1
        (r2, g2, b2) = c2
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
 
    colors = list(rgb_code_dictionary.keys())
    closest_colors = sorted(colors, key=lambda color: distance(color, point))
    closest_color = closest_colors[0]
    code = rgb_code_dictionary[closest_color]
    return code

def place_pixel(session, ax, ay, new_color):
    message = "Probing absolute pixel ({}, {})".format(ax, ay)
 
    r = session.get("http://reddit.com/api/place/pixel.json?x={}&y={}".format(ax, ay), timeout=5)
    if r.status_code != 200:
        print("ERROR: ", r.status_code)
        print(r.text)
        time.sleep(5)
        return

    data = r.json()
 
    old_color = data["color"] if "color" in data else 0

    if old_color == new_color:
        print("Skipping pixel ({}, {}): color #{} set by {}".format(ax, ay,
                new_color, data["user_name"] if "user_name" in data else "<nobody>"))
    else:
        print("Placing color #{} at ({}, {})".format(new_color, ax, ay))
        r = session.post("https://www.reddit.com/api/place/draw.json", data={
            "x": str(ax),
            "y": str(ay),
            "color": str(new_color)
        })

        data = r.json()

        if "error" not in data:
            message = "Placed color: waiting {} seconds."
        else:
            message = "Cooldown already active: waiting {} seconds."

        waitTime = int(data["wait_seconds"]) + 2
        while waitTime > 0:
            m = message.format(waitTime)
            time.sleep(1)
            waitTime -= 1
            if waitTime > 0:
                print(m, end="              \r")
            else:
                print(m)
 
        if "error" in data:
            place_pixel(session, ax, ay, new_color)
 
# From: http://stackoverflow.com/questions/27337784/how-do-i-shuffle-a-multidimensional-list-in-python
def shuffle2d(arr2d, rand=random):
    """Shuffes entries of 2-d array arr2d, preserving shape."""
    reshape = []
    data = []
    iend = 0
    for row in arr2d:
        data.extend(row)
        istart, iend = iend, iend+len(row)
        reshape.append((istart, iend))
    rand.shuffle(data)
    return [data[istart:iend] for (istart,iend) in reshape]

def main():
    if len(sys.argv) != 3:
        print('Usage: python3 place.py <reddit_username> <reddit_password>')
        sys.exit(1)

    img = Image.open(BytesIO(base64.b64decode(UW_LOGO)))
    username = sys.argv[1]
    password = sys.argv[2]

    session, err = login(username, password)

    if err:
        print("Error logging in: {}".format(err))
        sys.exit(1)

    arr2d = shuffle2d([[[i,j] for i in range(img.width)] for j in range(img.height)])
    total = img.width * img.height

    while True:
        print("Starting image placement for img height: {}, width: {}".format(img.height, img.width))
        for x in range(img.width):
            for y in range(img.height):
                xx = arr2d[x][y]
                pixel = img.getpixel((xx[0], xx[1]))
     
                if pixel[2] > 0:
                    pal = find_palette((pixel[0], pixel[1], pixel[2]))
                    ax = xx[0] + ORIGIN[0]
                    ay = xx[1] + ORIGIN[1]
                    place_pixel(session, ax, ay, pal)

        print("All pixels placed.")

if __name__ == '__main__':
    main()