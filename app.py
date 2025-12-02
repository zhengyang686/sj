import streamlit as st
import pandas as pd
from pathlib import Path
import zipfile, io, re, subprocess

st.set_page_config(page_title="CatADB", layout="wide")
st.title("🔬 催化剂-吸附质数据门户")

# ----------- 1. 递归扫描仓库根下所有文件夹 -----------
@st.cache_data(show_spinner=False)
def load_all_folders():
    # 用 commit id 当缓存键，任何 push 都会自动失效
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], encoding="utf-8").strip()
    root = Path(__file__).parent          # 仓库根
    rows = []
    # rglob 只拿“目录”
    for fd in root.rglob("*"):
        if not fd.is_dir():
            continue
        # 跳过隐藏目录和 .git
        if any(part.startswith(".") for part in fd.parts):
            continue
        cifs  = list(fd.glob("*.cif"))
        xlsx  = list(fd.glob("*.xlsx"))
        # 正则提取吸附位点 & N 配位（按你命名习惯）
        site = re.search(r"site_(\w+)", fd.name, re.I)
        nco  = re.search(r"N(\d+)",   fd.name, re.I)
        rows.append({
            "folder_name": fd.name,
            "rel_path":    fd.relative_to(root),   # 用于展示
            "abs_path":    fd,                     # 用于读文件
            "ads_site":    site.group(1) if site else "unknown",
            "n_coord":     int(nco.group(1)) if nco else 0,
            "cifs":        cifs,
            "xlsx":        xlsx,
            "file_cnt":    len(cifs) + len(xlsx)
        })
    return pd.DataFrame(rows)

df_all = load_all_folders()

if df_all.empty:
    st.warning("仓库里没找到任何含 cif/xlsx 的文件夹！")
    st.stop()

# ----------- 2. 侧边栏过滤 -----------
with st.sidebar:
    kw = st.text_input("搜索文件夹关键字", "")
    sites = ["全部"] + sorted(df_all["ads_site"].unique())
    site_sel = st.selectbox("吸附位点", sites)
    coords = ["全部"] + sorted(df_all["n_coord"].astype(str).unique())
    coord_sel = st.selectbox("N 配位数量", coords)

mask = df_all["folder_name"].str.contains(kw, case=False, na=False)
if site_sel != "全部": mask &= df_all["ads_site"] == site_sel
if coord_sel != "全部": mask &= df_all["n_coord"] == int(coord_sel)
df_show = df_all[mask]

st.info(f"共找到 {len(df_show)} 个文件夹")

# ----------- 3. 展示文件夹列表 -----------
disp_df = df_show.copy()
disp_df["cifs"] = disp_df["cifs"].apply(lambda lst: ", ".join(p.name for p in lst))
disp_df["xlsx"] = disp_df["xlsx"].apply(lambda lst: ", ".join(p.name for p in lst))

sel = st.dataframe(
    disp_df[["rel_path", "ads_site", "n_coord", "file_cnt"]],
    use_container_width=True,
    selection_mode="single-row",
    on_select="rerun",
    key="folder_tb"
)

if not sel["selection"]["rows"]:
    st.stop()
row = df_show.iloc[sel["selection"]["rows"][0]]
fd_path = row["abs_path"]

# ----------- 4. 右侧文件预览 / 下载 -----------
st.subheader(f"📁 {row['rel_path']}")
tab1, tab2, tab3 = st.tabs([f"cif ({len(row['cifs'])})",
                            f"Excel ({len(row['xlsx'])})",
                            "打包下载"])

with tab1:
    for cif in row["cifs"]:
        with open(cif, "rb") as f:
            st.download_button(f"📄 {cif.name}", f, file_name=cif.name)

with tab2:
    for xlsx in row["xlsx"]:
        df_x = pd.read_excel(xlsx, engine="openpyxl")
        st.markdown(f"**{xlsx.name}**")
        st.dataframe(df_x, use_container_width=True)
        with open(xlsx, "rb") as f:
            st.download_button("下载此表", f, file_name=xlsx.name)

with tab3:
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as z:
        for f in row["cifs"] + row["xlsx"]:
            z.write(f, arcname=f.relative_to(fd_path))
    zip_io.seek(0)
    st.download_button("📦 打包整个文件夹", zip_io,
                       file_name=f"{row['folder_name']}.zip")
