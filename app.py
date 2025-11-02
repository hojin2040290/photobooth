from flask import *
import cv2, os, numpy as np

app = Flask(__name__)

captures_base = os.path.join(app.root_path, "static", "captures")
os.makedirs(captures_base, exist_ok=True)

photo_save, ret, frame = None, None, None
selected_photo = []
frame_base = os.path.join(app.root_path, "static", "frames")
frame_path = frame_base
selected_frame = []
shot_index = 0

def load_overlays():
    exts = ("jpg", "jpeg", "png")
    overlays = []
    for idx in selected_frame:
        img = None
        for ext in exts:
            p1 = os.path.join(frame_path, f"frame{idx}.{ext}")
            p2 = os.path.join(frame_path, f"{idx}.{ext}")
            if os.path.exists(p1):
                img = cv2.imread(p1)
                if img is not None:
                    break
            if os.path.exists(p2):
                img = cv2.imread(p2)
                if img is not None:
                    break
        if img is not None:
            overlays.append(img)
    return overlays

def generate_frames():
    global ret, frame, shot_index
    cap = cv2.VideoCapture(1)
    ov_list = load_overlays()
    while True:
        ret, cam = cap.read()
        if not ret:
            break
        cam = cv2.flip(cam, 1)

        if len(ov_list) > 0 and shot_index < len(ov_list):
            h, w = cam.shape[:2]
            ov = ov_list[shot_index]
            ov = cv2.resize(ov, (w, h))
            a = (cv2.cvtColor(ov, cv2.COLOR_BGR2GRAY) > 5).astype(np.float32)
            a = cv2.GaussianBlur(a, (0, 0), 2.0)
            a3 = cv2.merge([a, a, a])
            cam = (ov * a3 + cam * (1 - a3)).astype(np.uint8)

        frame = cam
        ok, buffer = cv2.imencode('.jpg', frame)
        if not ok:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def home():
    global photo_save, selected_photo, selected_frame, shot_index
    selected_photo = []
    selected_frame = []
    shot_index = 0
    i = 1
    while os.path.exists(os.path.join(captures_base, str(i))):
        i += 1
    photo_save = os.path.join(captures_base, str(i))
    return render_template('index.html')

@app.route('/select_frame_page')
def select_frame_page():
    files = sorted([f for f in os.listdir(frame_path) if os.path.isfile(os.path.join(frame_path, f))])
    folder_rel = os.path.relpath(frame_path, app.root_path).replace(os.sep, '/')
    return render_template('select_frame.html', folder_rel=folder_rel, files=files)

@app.route('/select_frame/<int:item_id>', methods=['POST'])
def select_frame(item_id):
    files = sorted([f for f in os.listdir(frame_path) if os.path.isfile(os.path.join(frame_path, f))])
    if not 1 <= item_id <= len(files):
        return jsonify(status="error"), 400
    if item_id not in selected_frame:
        selected_frame.append(item_id)
        print(f'{frame_path}/frame{item_id} 선택, 현재: {selected_frame}')
    return jsonify(status="ok", id=item_id)

@app.route('/delete_frame/<int:item_id>', methods=['POST'])
def delete_frame(item_id):
    files = sorted([f for f in os.listdir(frame_path) if os.path.isfile(os.path.join(frame_path, f))])
    if not 1 <= item_id <= len(files):
        return jsonify(status="error"), 400
    if item_id in selected_frame:
        selected_frame.remove(item_id)
        print(f'{frame_path}/frame{item_id} 취소, 현재: {selected_frame}')
    return jsonify(status="ok", id=item_id)

@app.route("/photo_page")
def photo_page():
    return render_template("photo.html")

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['GET'])
def capture():
    global photo_save, ret, frame, shot_index
    os.makedirs(photo_save, exist_ok=True)
    if not ret:
        return "err", 500

    i = len([f for f in os.listdir(photo_save) if f.startswith('capture')]) + 1
    filename = f"capture{i}.jpg"
    cv2.imwrite(os.path.join(photo_save, filename), frame)
    print(f'{photo_save}/{filename} 이 촬영됨')

    shot_index += 1

    return "ok"

@app.route('/select_photo_page')
def select_photo_page():
    files = sorted([f for f in os.listdir(photo_save) if os.path.isfile(os.path.join(photo_save, f))])
    folder_rel = os.path.relpath(photo_save, app.root_path).replace(os.sep, '/')
    return render_template('select_photo.html', folder_rel=folder_rel, files=files)

@app.route('/select_photo/<int:item_id>', methods=['POST'])
def select_photo(item_id):
    global selected_photo
    files = sorted([f for f in os.listdir(photo_save) if os.path.isfile(os.path.join(photo_save, f))])
    if not 1 <= item_id <= len(files):
        return jsonify(status="error"), 400
    if item_id not in selected_photo:
        selected_photo.append(item_id)
        print(f'{photo_save}/capture{item_id}.jpg 선택, 현재: {selected_photo}')
    return jsonify(status="ok", id=item_id)

@app.route('/delete_photo/<int:item_id>', methods=['POST'])
def delete_photo(item_id):
    global selected_photo
    files = sorted([f for f in os.listdir(photo_save) if os.path.isfile(os.path.join(photo_save, f))])
    if not 1 <= item_id <= len(files):
        return jsonify(status="error"), 400
    if item_id in selected_photo:
        selected_photo.remove(item_id)
        print(f'{photo_save}/capture{item_id}.jpg 취소, 현재: {selected_photo}')
    return jsonify(status="ok", id=item_id)

@app.route('/edit_page')
def edit():
    selected_photo_filenames = [f"capture{i}.jpg" for i in selected_photo]
    folder_rel = os.path.relpath(photo_save, app.root_path).replace(os.sep, '/')
    return render_template('edit.html', folder_rel=folder_rel, selected_photo_filenames=selected_photo_filenames)

@app.route('/result_page')
def result():
    return render_template('result.html')

port_num = 5001
host_adress = '0.0.0.0'

if __name__ == '__main__':
    app.run(debug=False, threaded=True, host=host_adress, port=port_num)