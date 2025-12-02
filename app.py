import streamlit as st
import pandas as pd
from pathlib import Path
import zipfile, io, re
import py3Dmol
import streamlit.components.v1 as components

st.set_page_config(page_title="CatADB", layout="wide")
st.title("🔬 催化剂-吸附质数据门户（逐级浏览 + CIF 可视化）")

# ---------- 1. 解析文件夹名 ----------
def parse_name(fname: str):
    n = re.search(r"N(\d+)", fname, re.I)
    n_coord = int(n.group(1)) if n else 0
    for key in ["Br", "Bri", "atop"]:
        if key.lower() in fname.lower():
            return n_coord, key.rstrip("i")
    return n_coord, "unknown"

# ---------- 2. CIF 可视化 ----------
def view_cif(cif_path):
    with open(cif_path, "r", encoding="utf-8") as f:
        cif_txt = f.read()
    viewer = py3Dmol.view(width=400, height=300)
    viewer.addModel(cif_txt, "cif")
    viewer.setStyle({"stick": {"radius": 0.15}, "sphere": {"scale": 0.25}})
    viewer.zoomTo()
    viewer.render()
    return viewer

# ---------- 3. 当前目录导航 ----------
root = Path(__file__).parent
if "curr" not in st.session_state:
    st.session_state.curr = Path("")
curr: Path = st.session_state.curr
abs_curr = root / curr

# ---------- 4. 扫描当前层 ----------
folders = [p for p in abs_curr.iterdir() if p.is_dir()]
cifs    = list(abs_curr.glob("*.cif"))
xlsx    = list(abs_curr.glob("*.xlsx"))
n_coord, site = parse_name(curr.name)

# ---------- 5. 顶部信息 & 返回 ----------
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown(f"📂 **当前目录：** `{curr}`  | N 配位：**{n_coord}**  | 吸附位点：**{site}**")
with col2:
    if curr != Path(""):
        if st.button("← 返回上级"):
            st.session_state.curr = curr.parent
            st.rerun()

# ---------- 6. 自动分类卡片（当前层） ----------
if folders:
    st.header("📊 当前层自动分类")
    df_fold = pd.DataFrame([parse_name(fd.name) + (fd.name,) for fd in folders],
                           columns=["N", "site", "folder"])
    stats = df_fold.groupby(["site", "N"]).size().reset_index(name="count")
    cols = st.columns(len(stats))
    for col, (_, row) in zip(cols, stats.iterrows()):
        with col:
            st.metric(label=f"{row['site']} — N{row['N']}", value=row["count"])

# ---------- 7. 子文件夹（仅按钮） ----------
if folders:
    st.subheader("子文件夹")
    for fd in folders:
        if st.button(f"📁 {fd.name}", key=f"btn_{fd.name}"):
            st.session_state.curr = curr / fd.name
            st.rerun()
else:
    st.info("当前目录下无子文件夹")

# ---------- 8. CIF 可视化 ----------
if cifs:
    st.subheader("🔍 CIF 可视化")
    for f in cifs:
        col1, col2 = st.columns([1, 1])
        with col1:
            viewer = view_cif(f)
            components.html(viewer._repr_html_(), height=320)
        with col2:
            st.text(f"{f.name}")
            with open(f, "rb") as fp:
                st.download_button("下载 CIF", fp, file_name=f.name)

# ---------- 9. Excel 预览 / 下载 ----------
if xlsx:
    st.subheader("📊 Excel 预览")
    for f in xlsx:
        df_tmp = pd.read_excel(f, engine="openpyxl")
        st.markdown(f"**{f.name}**")
        st.dataframe(df_tmp, use_container_width=True)
        with open(f, "rb") as fp:
            st.download_button("下载表格", fp, file_name=f.name)

# ---------- 10. 打包当前目录 ----------
if cifs or xlsx:
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as z:
        for f in cifs + xlsx:
            z.write(f, arcname=f.name)
    zip_io.seek(0)
    st.download_button("📦 打包当前目录", zip_io, file_name=f"{curr.name or 'root'}.zip")
