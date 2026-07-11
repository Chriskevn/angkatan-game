from flask import Flask, render_template, request, jsonify
from pathlib import Path
import csv

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "people.csv"
FACES_DIR = BASE_DIR / "static" / "faces"


def clean_text(value):
    return "" if value is None else str(value).strip()


def detect_delimiter(header_line):
    if ";" in header_line and "," not in header_line:
        return ";"
    return ","


def resolve_image_filename(csv_name):
    """
    Supports both:
    - sc1_01.jpg
    - sc1_01.jpg.png
    """
    original = clean_text(csv_name)

    if (FACES_DIR / original).exists():
        return original

    with_png = original + ".png"
    if (FACES_DIR / with_png).exists():
        return with_png

    return original


def load_people():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"people.csv was not found at: {CSV_PATH}"
        )

    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        first_line = file.readline()
        file.seek(0)

        reader = csv.DictReader(
            file,
            delimiter=detect_delimiter(first_line)
        )

        required = {"id", "sc", "image", "nama_panggilan", "asal"}
        detected = {
            clean_text(field)
            for field in (reader.fieldnames or [])
        }

        missing = required - detected
        if missing:
            raise ValueError(
                "Missing CSV columns: "
                + ", ".join(sorted(missing))
                + ". Detected columns: "
                + ", ".join(sorted(detected))
            )

        people = []

        for row in reader:
            cleaned = {
                clean_text(key): clean_text(value)
                for key, value in row.items()
                if key is not None
            }

            if not cleaned.get("id"):
                continue

            cleaned["image_file"] = resolve_image_filename(
                cleaned["image"]
            )

            people.append(cleaned)

    people.sort(
        key=lambda person: (
            int(person["sc"]),
            int(person["id"])
        )
    )

    return people


PEOPLE = load_people()

@app.route("/")
def index():
    people = PEOPLE
    sc_list = sorted(
        {person["sc"] for person in people},
        key=int
    )

    return render_template(
        "index.html",
        people=people,
        sc_list=sc_list
    )


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json(force=True)

    person_id = clean_text(data.get("id"))
    target = clean_text(data.get("target"))
    guessed_name = clean_text(data.get("nama_panggilan"))
    guessed_asal = clean_text(data.get("asal"))

    people = load_people()

    person = next(
        (item for item in people if item["id"] == person_id),
        None
    )

    if person is None:
        return jsonify({
            "ok": False,
            "message": "Person not found."
        }), 404

    correct_name = person["nama_panggilan"]
    correct_asal = person["asal"]

    name_correct = guessed_name == correct_name
    asal_correct = guessed_asal == correct_asal

    if target == "name":
        correct = name_correct
    elif target == "asal":
        correct = asal_correct
    else:
        correct = name_correct and asal_correct

    return jsonify({
        "ok": True,
        "correct": correct,
        "name_correct": name_correct,
        "asal_correct": asal_correct,
        "correct_name": correct_name,
        "correct_asal": correct_asal
    })


if __name__ == "__main__":
    app.run(debug=True)
