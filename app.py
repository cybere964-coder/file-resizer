import io
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image
import pypdf
import pypdfium2 as pdfium

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # Max 25 MB upload limit


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "ফাইল সাইজ 25 MB-এর বেশি হতে পারবে না!"}), 413


def compress_jpg(file_bytes, target_bytes):
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    low, high = 10, 95
    best_data = None

    while low <= high:
        mid = (low + high) // 2
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=mid, optimize=True)
        size = buf.tell()
        if size <= target_bytes:
            best_data = buf.getvalue()
            low = mid + 1
        else:
            high = mid - 1

    if best_data is None:
        scale = 0.9
        while scale > 0.1:
            new_w = max(1, int(img.width * scale))
            new_h = max(1, int(img.height * scale))
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=30, optimize=True)
            if buf.tell() <= target_bytes:
                best_data = buf.getvalue()
                break
            scale -= 0.1

    if best_data is None:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=10, optimize=True)
        best_data = buf.getvalue()

    return best_data


def increase_jpg(file_bytes, target_bytes):
    current_size = len(file_bytes)
    if current_size >= target_bytes:
        return file_bytes
    padding = b"\x00" * (target_bytes - current_size)
    return file_bytes + padding


def compress_pdf(file_bytes, target_bytes):
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    writer = pypdf.PdfWriter()

    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)

    buf = io.BytesIO()
    writer.write(buf)
    if buf.tell() <= target_bytes:
        return buf.getvalue()

    pdf = pdfium.PdfDocument(file_bytes)
    for scale in [1.5, 1.0, 0.75, 0.5]:
        for quality in [70, 50, 35, 20]:
            jpeg_pages = []
            for i in range(len(pdf)):
                page = pdf[i]
                bitmap = page.render(scale=scale)
                pil_img = bitmap.to_pil().convert("RGB")
                img_buf = io.BytesIO()
                pil_img.save(img_buf, format="JPEG", quality=quality, optimize=True)
                jpeg_pages.append(img_buf.getvalue())

            new_writer = pypdf.PdfWriter()
            for img_bytes in jpeg_pages:
                img_pil = Image.open(io.BytesIO(img_bytes))
                pdf_page_buf = io.BytesIO()
                img_pil.save(pdf_page_buf, format="PDF")
                img_reader = pypdf.PdfReader(io.BytesIO(pdf_page_buf.getvalue()))
                new_writer.add_page(img_reader.pages[0])

            out_buf = io.BytesIO()
            new_writer.write(out_buf)
            if out_buf.tell() <= target_bytes:
                return out_buf.getvalue()

    return buf.getvalue()


def increase_pdf(file_bytes, target_bytes):
    current_size = len(file_bytes)
    if current_size >= target_bytes:
        return file_bytes
    needed = target_bytes - current_size
    header = b"\n%"
    if needed <= len(header):
        padding = b"\n" * needed
    else:
        padding = header + (b"0" * (needed - len(header)))
    return file_bytes + padding


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "কোনো ফাইল আপলোড করা হয়নি!"}), 400

    file = request.files["file"]
    mode = request.form.get("mode")
    try:
        target_kb = float(request.form.get("target_kb", 0))
    except ValueError:
        return jsonify({"error": "সঠিক টার্গেট সাইজ দিন!"}), 400

    if file.filename == "" or target_kb <= 0:
        return jsonify({"error": "সঠিক ফাইল এবং টার্গেট সাইজ দিন!"}), 400

    filename = file.filename.lower()
    file_bytes = file.read()
    target_bytes = int(target_kb * 1024)
    current_bytes = len(file_bytes)

    if mode == "compress" and current_bytes <= target_bytes:
        return jsonify({
            "error": f"ফাইলের বর্তমান সাইজ ({current_bytes/1024:.1f} KB) ইতিমধ্যেই টার্গেট সাইজের চেয়ে ছোট!"
        }), 400

    if mode == "increase" and current_bytes >= target_bytes:
        return jsonify({
            "error": f"ফাইলের বর্তমান সাইজ ({current_bytes/1024:.1f} KB) ইতিমধ্যেই টার্গেট সাইজের চেয়ে বড়!"
        }), 400

    if filename.endswith((".jpg", ".jpeg")):
        out_bytes = compress_jpg(file_bytes, target_bytes) if mode == "compress" else increase_jpg(file_bytes, target_bytes)
        mimetype = "image/jpeg"
        out_name = f"{mode}_{file.filename}"
    elif filename.endswith(".pdf"):
        out_bytes = compress_pdf(file_bytes, target_bytes) if mode == "compress" else increase_pdf(file_bytes, target_bytes)
        mimetype = "application/pdf"
        out_name = f"{mode}_{file.filename}"
    else:
        return jsonify({"error": "শুধুমাত্র .JPG এবং .PDF ফাইল সাপোর্ট করে!"}), 400

    return send_file(
        io.BytesIO(out_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=out_name,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
