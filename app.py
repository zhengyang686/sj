import streamlit as st
import pandas as pd
from pathlib import Path
import zipfile, io, re, os

st.set_page_config(page_title="CatADB", layout="wide")
st.title("🔬 催化剂-吸附质数据门户")

# ----------- 1. 直接读仓库里的 Fe-Ni-N5-Br/ -----------
@st.cache_data(show_spinner=False)
def load_once():
    base = Path(__file__).parent / "Fe-Ni-N5-Br"
    if not base.exists():
        st.error("仓库里未找到 Fe-Ni-N5-Br 文件夹！")
        st.stop()
    rows = []
    for fd in base.iterdir():
        if not fd.is_dir():
            continue
        cifs   = list(fd.glob("*.cif"))
        xlsx   = list(fd.glob("*.xlsx"))
        # 从文件夹名里抓“吸附位点”和“N配位”
        site = re.search(r"site_(\w+)", fd.name, re.I)
        nco  = re.search(r"N(\d+)",   fd.name, re.I)
        rows.append({
            "folder":   fd.name,
            "path":     fd,
            "ads_site": site.group(1) if site else "unknown",
            "n_coord":  int(nco.group(1)) if nco else 0,
            "cifs":     cifs,
            "xlsx":     xlsx
        })
    return pd.DataFrame(rows)

df_all = load_once()

# ----------- 2. 左侧过滤 -----------
with st.sidebar:
    kw   = st.text_input("搜索文件夹关键字", "")
    sites = ["全部"] + sorted(df_all["ads_site"].unique())
    site_sel = st.selectbox("吸附位点", sites)
    coords = ["全部"] + sorted(df_all["n_coord"].astype(str).unique())
    coord_sel = st.selectbox("N 配位数量", coords)

mask = df_all["folder"].str.contains(kw, case=False, na=False)
if site_sel != "全部": mask &= df_all["ads_site"] == site_sel
if coord_sel != "全部": mask &= df_all["n_coord"] == int(coord_sel)
df_show = df_all[mask]

# ----------- 3. 展示表（字符串） -----------
disp_df = df_show.copy()
disp_df["cifs"] = disp_df["cifs"].apply(lambda lst: ", ".join(p.name for p in lst))
disp_df["xlsx"] = disp_df["xlsx"].apply(lambda lst: ", ".join(p.name for p in lst))

sel = st.dataframe(
    disp_df[["folder","ads_site","n_coord","cifs","xlsx"]],
    use_container_width=True,
    selection_mode="single-row",
    on_select="rerun",
    key="tb"
)

if not sel["selection"]["rows"]:
    st.stop()
row  = df_show.iloc[sel["selection"]["rows"][0]]
fd_path = row["path"]

# ----------- 4. 右侧详情 -----------
st.subheader(f"📁 {row['folder']}")
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
                       file_name=f"{row['folder']}.zip")