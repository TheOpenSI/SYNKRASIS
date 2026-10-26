# =============================================================================================
# One-time setup of the persistent BigCodeBench container "synk_bcb". Run it once on every machine, it needs network:
#
#   python services/Container/prepare_bcb_container.py
#
# BigCodeBench tasks use many libraries (data/BigCodeBench/requirements_pinned.txt, the versions the tasks were written
# for). They are installed once, in the container, and every attempt of the experiments reuses the container 
# (docker start), only the files of the attempt change.
# The script:
#   1. creates the container (network on) and installs the libraries,
#   2. downloads the nltk data the tasks use,
#   3. cuts the network of the container, so the generated code cannot reach the internet,
#   4. checks that the libraries import and that there is no network.
# If the container exists already only step 4 runs. To prepare again: docker rm -f synk_bcb
# =============================================================================================

import os
import shutil
import subprocess
import sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from services.Container.Container import Container

CONTAINER_NAME = "synk_bcb"
MOUNT_DIR_NAME = "synk_bcb_mount"
RUN_OPTIONS = ["--memory", "6g", "--cpus", "2", "--pids-limit", "512"]

NLTK_DATA = ["punkt", "punkt_tab", "stopwords", "wordnet", "omw-1.4", "averaged_perceptron_tagger",
             "averaged_perceptron_tagger_eng", "vader_lexicon", "words", "brown", "movie_reviews", "treebank"]

SETUP_MAIN = f"""
import nltk
for package in {NLTK_DATA!r}:
    print("nltk", package, nltk.download(package, quiet=True))
"""

CHECK_MAIN = """
import importlib, urllib.request
modules = "pandas numpy scipy statsmodels sympy sklearn keras tensorflow gensim PIL skimage cv2 pytesseract librosa soundfile nltk textblob wordcloud wordninja Levenshtein flask flask_mail flask_wtf flask_restful flask_login werkzeug django requests bs4 lxml pyquery mechanize xmltodict geopandas shapely geopy folium openpyxl xlwt docx cryptography Crypto rsa blake3 yaml chardet matplotlib seaborn prettytable texttable natsort holidays faker psutil pytz dateutil sendgrid wtforms wikipedia".split()
failed = []
for module in modules:
    try:
        importlib.import_module(module)
    except Exception as error:
        failed.append(f"{module}: {type(error).__name__}")
print("CHECK libraries that do not import:", failed if failed else "none")
try:
    urllib.request.urlopen("https://pypi.org", timeout=8)
    print("CHECK network: REACHABLE")
except Exception:
    print("CHECK network: none")
"""


def container_exists() -> bool:
    listing = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True).stdout
    return CONTAINER_NAME in listing.split()


def main() -> None:
    existed = container_exists()
    container = Container(container_name = CONTAINER_NAME,
                          mount_dir_name = MOUNT_DIR_NAME,
                          timeout = None,
                          run_options = RUN_OPTIONS)
    mount_dir = container.MOUNT_DIR_PATH

    if not existed:
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "BigCodeBench", "requirements_pinned.txt"),
                    os.path.join(mount_dir, "requirements.txt"))
        with open(os.path.join(mount_dir, "main.py"), "w") as main_file:
            main_file.write(SETUP_MAIN)
        container.start_container()                                  # creates the container, start.sh installs the libraries
        os.remove(os.path.join(mount_dir, "requirements.txt"))       # so the next starts do not run pip again
        subprocess.run(["docker", "network", "disconnect", "bridge", CONTAINER_NAME], capture_output=True)

    with open(os.path.join(mount_dir, "main.py"), "w") as main_file:
        main_file.write(CHECK_MAIN)
    response = container.start_container()
    for line in response.stdout.splitlines():
        if line.startswith("CHECK"):
            print(line)


if __name__ == "__main__":
    main()
