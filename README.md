# JPG & PDF Size Tool

A lightweight dark-themed Flask web application to compress or increase the file size (in KB or MB) of `.jpg`, `.jpeg`, and `.pdf` files.

## Features
- **Compress & Increase Modes:** Reduce file size via quality/DPI optimization or pad files safely to a target size.
- **KB & MB Unit Selector:** Set target sizes in either KB or MB.
- **Drag & Drop Upload:** Supports drag-and-drop as well as file picker upload.
- **In-Memory Processing:** Processes files in memory without storing user uploads on disk.
_ **The size of all multiple files will be reduced or increased.

## Project Structure
```text
file-resizer-app/
├── app.py
├── requirements.txt
├── README.md
└── templates/
    └── index.html
```

## Local Setup & Run
```bash
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000` in your browser.

## Cloud Deployment (Render / Railway)
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
