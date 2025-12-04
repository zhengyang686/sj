##############################
#  CatADB – 模块化强化版
#  功能：
#   - 首页介绍
#   - N 配位 / 吸附位点模块化分区
#   - CIF 可视化
#   - Excel 预览
#   - 打包下载
##############################

import streamlit as st
import pandas as pd
from pathlib import Path
import zipfile, io, re
import streamlit.components.v1 as components
import py3Dmol  # 用于依赖，无需 IPython

# =============================
# Streamlit 设置
# =============================
st.set_page_config(page_title="CatADB", layout="wide")
st.title("🔬 CatADB – 催化剂数据库（模块化分区）")

# =============================
# 首页介绍
# =============================
st.markdown("""
欢迎使用 **CatADB** 数据库！  
本数据库收集了催化剂基底及其吸附结构数据，包括 H、HO、O、2H、2O、2HO 等吸附结构的 CIF 文件以及对应 Excel 吸附能表格。

功能说明：  
- 左侧选择 N 配位或吸附位点进行分区  
- 点击分区按钮，显示对应子文件夹  
- 支持 CIF 可视化、Excel 查看与下载  
- 可打包下载整个文件夹  
""")

# =============================
# 文件夹名解析函数
# =============================
def parse_name(fname: str):
    n_match = re.search(r"N(\d+)", fname, re.I)
    n_coord = int(n_match.group(1)) if n_match else 0
    for key in ["Br", "Bri", "atop"]:
        if key.lower() in fname.lower():
            return n_coord, key.rstrip("i")
    return n_coord, "unknown"

# =============================
# CIF 可视化函数
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
# 当前目录
# =============================
root = Path(__file__).parent
if "curr" not in st.session_state:
    st.session_state.curr = Path("")
curr = st.session_state.curr
abs_curr = root / curr

# =============================
# 扫描子文件夹
# =============================
folders = sorted([p for p in abs_curr.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
cif_files = sorted(list(abs_curr.glob("*.cif")), key=lambda p: p.name.lower())
xlsx_files = sorted(list(abs_curr.glob("*.xlsx")), key=lambda p: p.name.lower())

# =============================
# 模块：返回上级
# =============================
if curr != Path(""):
    if st.button("← 返回上级目录"):
        st.session_state.curr = curr.parent
        st.rerun()

# =============================
# 模块：侧边栏选择 N 配位 / 吸附位点
# =============================
st.sidebar.header("🔹 模块化分区选择")
all_n = sorted(list({parse_name(f.name)[0] for f in folders}))
all_sites = sorted(list({parse_name(f.name)[1] for f in folders}))

sel_n = st.sidebar.selectbox("选择 N 配位", ["全部"] + all_n)
sel_site = st.sidebar.selectbox("选择吸附位点", ["全部"] + all_sites)

# =============================
# 模块：过滤文件夹
# =============================
def filter_folders(folders, n_val, site_val):
    filtered = []
    for f in folders:
        n, s = parse_name(f.name)
        if (n_val == "全部" or n_val == n) and (site_val == "全部" or site_val == s):
            filtered.append(f)
    return filtered

folders = filter_folders(folders, sel_n, sel_site)

# =============================
# 模块：显示分区文件夹
# =============================
if folders:
    st.header("📁 分区文件夹")
    for fd in folders:
        if st.button(f"📂 {fd.name}", key=f"btn_{fd.name}"):
            st.session_state.curr = curr / fd.name
            st.rerun()
else:
    st.info("无符合条件的文件夹")

# =============================
# 模块：CIF 可视化
# =============================
if cif_files:
    st.header("🔍 CIF 可视化")
    for f in cif_files:
        col1, col2 = st.columns([1,1])
        with col1:
            components.html(view_cif(f), height=320)
        with col2:
            st.write(f"**{f.name}**")
            with open(f, "rb") as fp:
                st.download_button("下载 CIF", fp, file_name=f.name)

# =============================
# 模块：Excel 预览
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
# 模块：打包下载
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
