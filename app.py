import streamlit as st
import pandas as pd
from pathlib import Path
import zipfile, io, re

st.set_page_config(page_title="CatADB", layout="wide")
st.title("🔬 催化剂-吸附质数据门户（文件夹浏览器）")

# ---------- 1. 当前目录导航 ----------
root = Path(__file__).parent
if "curr" not in st.session_state:
    st.session_state.curr = Path("")          # 相对根目录

curr: Path = st.session_state.curr
abs_curr = root / curr

# ---------- 2. 扫描当前层 ----------
folders = [p for p in abs_curr.iterdir() if p.is_dir()]
cifs    = list(abs_curr.glob("*.cif"))
xlsx    = list(abs_curr.glob("*.xlsx"))

# ---------- 3. 顶部导航栏 ----------
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown(f"📂 **当前目录：** `{curr}`")
with col2:
    if curr != Path(""):
        if st.button("← 返回上级"):
            st.session_state.curr = curr.parent
            st.rerun()

# ---------- 4. 当前层文件夹列表 ----------
if folders:
    st.subheader("子文件夹")
    for fd in folders:
        site = re.search(r"site_(\w+)", fd.name, re.I)
        nco  = re.search(r"N(\d+)",   fd.name, re.I)
        c1, c2 = len(list(fd.glob("*.cif"))), len(list(fd.glob("*.xlsx")))
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            if st.button(f"📁 {fd.name}", key=f"btn_{fd.name}"):
                st.session_state.curr = curr / fd.name
                st.rerun()
        with col2:
            st.caption("吸附位点")
            st.text(site.group(1) if site else "-")
        with col3:
            st.caption("N 配位")
            st.text(nco.group(1) if nco else "-")
else:
    st.info("当前目录下无子文件夹")

# ---------- 5. 当前层文件预览 / 下载 ----------
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
