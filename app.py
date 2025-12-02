import streamlit as st
import pandas as pd
from pathlib import Path
import zipfile, io, re

st.set_page_config(page_title="CatADB", layout="wide")
st.title("🔬 催化剂-吸附质数据门户（逐级浏览）")

# ---------- 1. 解析文件夹名 ----------
def parse_name(fname: str):
    n = re.search(r"N(\d+)", fname, re.I)
    n_coord = int(n.group(1)) if n else 0
    for key in ["Br", "Bri", "atop"]:
        if key.lower() in fname.lower():
            return n_coord, key.rstrip("i")
    return n_coord, "unknown"

# ---------- 2. 当前目录导航 ----------
root = Path(__file__).parent
if "curr" not in st.session_state:
    st.session_state.curr = Path("")
curr: Path = st.session_state.curr
abs_curr = root / curr

# ---------- 3. 扫描当前层 ----------
folders = [p for p in abs_curr.iterdir() if p.is_dir()]
cifs    = list(abs_curr.glob("*.cif"))
xlsx    = list(abs_curr.glob("*.xlsx"))
n_coord, site = parse_name(curr.name)

# ---------- 4. 顶部信息 & 返回 ----------
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown(f"📂 **当前目录：** `{curr}`  | N 配位：**{n_coord}**  | 吸附位点：**{site}**")
with col2:
    if curr != Path(""):
        if st.button("← 返回上级"):
            st.session_state.curr = curr.parent
            st.rerun()

# ---------- 5. 子文件夹（按钮进入） ----------
if folders:
    st.subheader("子文件夹")
    for fd in folders:
    nc, st_site = parse_name(fd.name)
    c1, c2 = len(list(fd.glob("*.cif"))), len(list(fd.glob("*.xlsx")))
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if st.button(f"📁 {fd.name}", key=f"btn_{fd.name}"):
            st.session_state.curr = curr / fd.name
            st.rerun()
    with col2:
        st.caption("吸附位点")
        st.text(st_site)
    with col3:
        st.caption("N 配位")
        st.text(str(nc))
else:
    st.info("当前目录下无子文件夹")

# ---------- 6. 当前目录文件 ----------
if cifs or xlsx:
    st.subheader("当前目录文件")
    tab1, tab2, tab3 = st.tabs([f"cif ({len(cifs)})", f"Excel ({len(xlsx)})", "打包当前目录"])
    with tab1:
        for f in cifs:
            with open(f, "rb") as fp:
                st.download_button(f"📄 {f.name}", fp, file_name=f.name)
    with tab2:
        for f in xlsx:
            df_tmp = pd.read_excel(f, engine="openpyxl")
            st.markdown(f"**{f.name}**")
            st.dataframe(df_tmp, use_container_width=True)
            with open(f, "rb") as fp:
                st.download_button("下载此表", fp, file_name=f.name)
    with tab3:
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, "w") as z:
            for f in cifs + xlsx:
                z.write(f, arcname=f.name)
        zip_io.seek(0)
        st.download_button("📦 打包下载", zip_io, file_name=f"{curr.name or 'root'}.zip")
else:
    st.info("当前目录下无 cif/xlsx 文件")

