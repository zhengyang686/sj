##############################
#  CatADB – 强化版
#  新增：搜索 + 分类分区
##############################

import streamlit as st
import pandas as pd
from pathlib import Path
import zipfile, io, re
import streamlit.components.v1 as components
import py3Dmol   # 用于依赖，不使用 IPython

# =============================
# Streamlit 设置
# =============================
st.set_page_config(page_title="CatADB", layout="wide")
st.title("🔬 催化剂-吸附质数据门户（搜索 + 分区 + CIF 可视化）")

# =============================
# 1. 文件夹名解析函数
# =============================
def parse_name(fname: str):
    """
    从文件夹名中提取：
      - N 配位数（如 N3）
      - 吸附位点（Br、Bri、atop）
    """
    n_match = re.search(r"N(\d+)", fname, re.I)
    n_coord = int(n_match.group(1)) if n_match else 0

    for key in ["Br", "Bri", "atop"]:
        if key.lower() in fname.lower():
            return n_coord, key.rstrip("i")

    return n_coord, "unknown"


# =============================
# 2. CIF 可视化（绕过 IPython）
# =============================
def view_cif(cif_path):
    with open(cif_path, "r", encoding="utf-8") as f:
        cif_txt = f.read()

    html = f"""
    <div id="view-{hash(cif_path)}" style="height: 300px;"></div>
    <script src="https://3dmol.org/build/3Dmol-min.js"></script>
    <script>
        var viewer = $3Dmol.createViewer('view-{hash(cif_path)}');
        viewer.addModel(`{cif_txt}`, 'cif');
        viewer.setStyle({{stick: {{radius: 0.15}}, sphere: {{scale: 0.25}}}});
        viewer.zoomTo();
        viewer.render();
    </script>
    """
    return html


# =============================
# 3. 当前目录状态
# =============================
root = Path(__file__).parent

if "curr" not in st.session_state:
    st.session_state.curr = Path("")

curr: Path = st.session_state.curr
abs_curr = root / curr


# =============================
# 4. 扫描当前层的内容
# =============================
folders = [p for p in abs_curr.iterdir() if p.is_dir()]
cif_files = list(abs_curr.glob("*.cif"))
xlsx_files = list(abs_curr.glob("*.xlsx"))

n_coord, site = parse_name(curr.name)


# =============================
# 5. 顶部信息 & 返回
# =============================
st.markdown(f"📂 **当前目录：** `{curr}` | N 配位：**{n_coord}** | 吸附位点：**{site}**")

if curr != Path(""):
    if st.button("← 返回上级目录"):
        st.session_state.curr = curr.parent
        st.rerun()


# =============================
# 6. 搜索功能（新增）
# =============================
st.sidebar.header("🔍 搜索")
keyword = st.sidebar.text_input("搜索当前目录内文件 / 文件夹", "")

def match(pattern, name):
    return pattern.lower() in name.lower()

if keyword.strip():
    folders = [f for f in folders if match(keyword, f.name)]
    cif_files = [f for f in cif_files if match(keyword, f.name)]
    xlsx_files = [f for f in xlsx_files if match(keyword, f.name)]


# =============================
# 7. 分类分区（N 配位 + 吸附位点）
# =============================
if folders:
    st.header("📊 文件夹分类（按 N 配位 + 吸附位点）")

    # 生成 dataframe
    df_folder = pd.DataFrame(
        [parse_name(fd.name) + (fd,) for fd in folders],
        columns=["N", "site", "path"]
    )

    # 分区显示
    for (N, site), subdf in df_folder.groupby(["N", "site"]):
        st.subheader(f"### 🧩 分区：N{N} | {site}")

        for fd in subdf["path"]:
            if st.button(f"📁 {fd.name}", key=f"btn_{fd.name}"):
                st.session_state.curr = curr / fd.name
                st.rerun()


# =============================
# 8. CIF 可视化
# =============================
if cif_files:
    st.header("🔍 CIF 可视化")
    for f in cif_files:
        left, right = st.columns([1, 1])
        with left:
            components.html(view_cif(f), height=320)
        with right:
            st.write(f"**{f.name}**")
            with open(f, "rb") as fp:
                st.download_button("下载 CIF", fp, file_name=f.name)


# =============================
# 9. Excel 预览
# =============================
if xlsx_files:
    st.header("📊 Excel 预览")
    for f in xlsx_files:
        df_x = pd.read_excel(f, engine="openpyxl")
        st.write(f"### {f.name}")
        st.dataframe(df_x, use_container_width=True)
        with open(f, "rb") as fp:
            st.download_button("下载 Excel", fp, file_name=f.name)


# =============================
# 10. 打包下载
# =============================
if cif_files or xlsx_files:
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as z:
        for f in cif_files + xlsx_files:
            z.write(f, arcname=f.name)
    zip_io.seek(0)
    st.download_button(
        "📦 打包下载当前目录全部文件",
        zip_io,
        file_name=f"{curr.name or 'root'}.zip"
    )
