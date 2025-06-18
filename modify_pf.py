import os
import shutil
import glob
import re

def prepare_dest_folder(dest_folder, preserve_dir="DTM"):
    """
    如果 dest_folder 不存在则创建；如果存在，则删除其下
    除 preserve_dir 外的所有文件和子目录。
    """
    os.makedirs(dest_folder, exist_ok=True)
    for entry in os.listdir(dest_folder):
        if entry == preserve_dir:
            continue
        path = os.path.join(dest_folder, entry)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def copy_pf_folder(src_folder, dest_folder, preserve_dir="DTM"):
    """
    将 src_folder 下的所有文件和子目录复制到 dest_folder，
    跳过名为 preserve_dir 的子目录；dest_folder 下同名
    preserve_dir 保留不变。
    """
    prepare_dest_folder(dest_folder, preserve_dir)

    for entry in os.listdir(src_folder):
        if entry == preserve_dir:
            continue
        src_path = os.path.join(src_folder, entry)
        dst_path = os.path.join(dest_folder, entry)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)


def get_title_ranges_in_pf(content):
    lines = content.splitlines()
    blocks = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            body = stripped[1:].strip()
            if not body:
                continue
            title = body.split()[0]
            blocks.append({"title": title, "start_line": i+1, "end_line": None})
    for j in range(len(blocks)):
        if j < len(blocks) - 1:
            blocks[j]["end_line"] = blocks[j+1]["start_line"] - 1
        else:
            blocks[j]["end_line"] = len(lines)
    return blocks


def modify_pf_file(file_path, modifications,
                   enable_model_filename=False,
                   enable_start_elev_offset=False):
    raw_filename = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
        lines = f.readlines()
    content = "".join(lines)
    blocks = get_title_ranges_in_pf(content)

    new_lines = []
    cur = 1
    for blk in blocks:
        title = blk["title"]
        start, end = blk["start_line"], blk["end_line"]

        # 保留块前内容
        while cur < start:
            new_lines.append(lines[cur-1])
            cur += 1

        # 注释"地面线"
        if title == "地面线":
            for idx in range(start-1, end):
                new_lines.append(f"//{lines[idx].rstrip()}\n")
            cur = end + 1
            continue

        # 提取 tokens
        if title in modifications or (enable_start_elev_offset and title == "起点设计标高"):
            tokens = []
            for idx in range(start-1, end):
                raw = lines[idx].split("//", 1)[0]
                stripped = raw.lstrip()
                if stripped.startswith("#"):
                    parts = stripped[1:].strip().split()
                    tokens.extend(parts[1:])
                else:
                    tokens.extend(stripped.split())

            # 可选：起点设计标高 +0.3
            if enable_start_elev_offset and title == "起点设计标高" and tokens:
                try:
                    tokens[0] = str(float(tokens[0]) + 0.3)
                except ValueError:
                    pass

            # 静态 mods
            if title in modifications:
                for idx, val in modifications[title].items():
                    if idx >= len(tokens):
                        tokens.extend([""] * (idx - len(tokens) + 1))
                    tokens[idx] = val

            # 可选模型文件名
            if title == "模型管理" and enable_model_filename:
                if len(tokens) < 2:
                    tokens.extend([""] * (2 - len(tokens)))
                tokens[1] = raw_filename

            # --- Updated 断链 section in modify_pf_file() ---
            if title == "断链":
                # 新增功能：检查断链部分是否小于15个元素
                if len(tokens) < 15:
                    print(f"缺少断链！文件: {file_path}, 断链元素数量: {len(tokens)}")
                
                # 处理第4和第10个token，并保留两端双引号
                for idx, label in [(4, "改移道路起点道"), (10, "改移道路终点道")]:
                    # 确保tokens长度足够
                    if idx >= len(tokens):
                        tokens.extend([""] * (idx - len(tokens) + 1))
                    val = tokens[idx]
                    # 删除小数点及其后的数字
                    val = re.sub(r"\.\d+", "", val)
                    # 提取形如 K数字+数字 的段落
                    m = re.search(r"(K\d+\+\d+)", val)
                    if m:
                        segment = m.group(1)
                        # 构造带双引号的新token
                        tokens[idx] = f"\"{label}{segment}\""
                    else:
                        # 若未匹配，则保留K及其后续内容，并加双引号
                        suffix = re.sub(r"^.*?K", "", val)
                        tokens[idx] = f"\"{label}K{suffix}\""
                # 后续保持原有的格式化输出逻辑

            # 格式化输出
            if title == "断链":
                lines_out = [f"#{title} {tokens[0]}"] if tokens else [f"#{title}"]
                rest = tokens[1:] if tokens else []
                for i in range(0, len(rest), 7):
                    lines_out.append(" ".join(rest[i:i+7]))
                new_block = "\n".join(lines_out) + "\n"

            elif title == "模型管理":
                lines_out = [f"#{title}", " ".join(tokens)] if tokens else [f"#{title}"]
                new_block = "\n".join(lines_out) + "\n"

            else:
                new_block = "#" + title + (" " + " ".join(tokens) if tokens else "") + "\n"

            new_lines.append(new_block)
            cur = end + 1

        else:
            # 原样保留
            while cur <= end:
                new_lines.append(lines[cur-1])
                cur += 1

    # 尾部
    while cur <= len(lines):
        new_lines.append(lines[cur-1])
        cur += 1

    with open(file_path, 'w', encoding='gbk', errors='ignore') as f:
        f.writelines(new_lines)
    print(f"Modified: {file_path}")

if __name__ == "__main__":
    src_folder  = r"C:\Users\Public\Nwt\cache\recv\徐晨宇\沪甬联络线"
    dest_folder = "modified"

    enable_model_filename = True
    enable_start_elev_offset = False

    mods = {
        "绘图比例":   {1: "1000", 2: "200"},
        "断链":       {3: "\"\"", 11: "\"\""},
        "模型管理":   {5: "改移道路"},
        "数模":       {0: "2000地形图总和-8号色"},
        "五线谱":     {0: "复杂的改移公道路纵断面"},
    }

    copy_pf_folder(src_folder, dest_folder, preserve_dir="DTM")

    for pf_file in glob.glob(os.path.join(dest_folder, "*.pf")):
        modify_pf_file(pf_file, mods,
                       enable_model_filename=True,
                       enable_start_elev_offset=enable_start_elev_offset)

    print("All .pf files have been processed.")