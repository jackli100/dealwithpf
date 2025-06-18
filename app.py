from flask import Flask, request, render_template, send_file
import os
import tempfile
from modify_pf import modify_pf_file

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        pf_file = request.files.get('pf_file')
        if not pf_file:
            return render_template('index.html', message='请上传 .pf 文件')
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, pf_file.filename)
            pf_file.save(input_path)
            mods = {
                '绘图比例': {1: '1000', 2: '200'},
                '断链': {3: '""', 11: '""'},
                '模型管理': {5: '改移道路'},
                '数模': {0: '2000地形图总和-8号色'},
                '五线谱': {0: '复杂的改移公道路纵断面'},
            }
            modify_pf_file(input_path, mods, enable_model_filename=True)
            return send_file(input_path, as_attachment=True)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
