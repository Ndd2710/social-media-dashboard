import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Social Media Dashboard", page_icon="📊", layout="wide")

DATA_FILE = "data_features.xlsx"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PARTIAL_MONTH = "2025-05"   # tháng chỉ có 10 bài, bỏ khỏi biểu đồ xu hướng


# ---------- Nạp dữ liệu ----------
@st.cache_data
def load_data():
    df = pd.read_excel(DATA_FILE, sheet_name="Data_Features")
    df["Post_Date"] = pd.to_datetime(df["Post_Date"])
    df["Weekday"] = pd.Categorical(df["Weekday"], categories=WEEKDAYS, ordered=True)
    return df


df = load_data()

# ---------- Tiêu đề + nút làm mới ----------
head_l, head_r = st.columns([5, 1])
head_l.title("📊 Dashboard hiệu suất nội dung mạng xã hội")
head_l.caption("Dữ liệu: 5.600 lượt đăng, 6 nền tảng, 8 quốc gia (01/2024 – 05/2025)")
if head_r.button("🔄 Làm mới dữ liệu"):
    st.cache_data.clear()
    st.rerun()

# ---------- Bộ lọc ----------
st.sidebar.header("Bộ lọc")

platforms = st.sidebar.multiselect("Nền tảng", sorted(df["Platform"].unique()),
                                   default=sorted(df["Platform"].unique()))
post_types = st.sidebar.multiselect("Định dạng bài", sorted(df["Post_Type"].unique()),
                                    default=sorted(df["Post_Type"].unique()))
content_types = st.sidebar.multiselect("Loại nội dung", sorted(df["Content_Type"].unique()),
                                       default=sorted(df["Content_Type"].unique()))
regions = st.sidebar.multiselect("Quốc gia", sorted(df["Region"].unique()),
                                 default=sorted(df["Region"].unique()))

min_d, max_d = df["Post_Date"].min().date(), df["Post_Date"].max().date()
date_range = st.sidebar.date_input("Khoảng ngày", value=(min_d, max_d),
                                   min_value=min_d, max_value=max_d)
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = date_range
else:                       # người dùng mới chọn 1 ngày
    start, end = min_d, max_d

f = df[
    df["Platform"].isin(platforms)
    & df["Post_Type"].isin(post_types)
    & df["Content_Type"].isin(content_types)
    & df["Region"].isin(regions)
    & (df["Post_Date"].dt.date >= start)
    & (df["Post_Date"].dt.date <= end)
]

if f.empty:
    st.warning("Không có dữ liệu phù hợp với bộ lọc. Hãy nới lỏng bộ lọc ở thanh bên.")
    st.stop()

# ---------- Thẻ chỉ số ----------
click_rows = f[f["Has_Click_Data"]]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Số lượt đăng", f"{len(f):,}")
k2.metric("Tổng lượt xem", f"{f['Views'].sum() / 1e6:,.0f} triệu")
k3.metric("Engagement Rate TB", f"{f['Engagement_Rate'].mean():.1%}")
k4.metric("CTR TB", f"{click_rows['Click_Through_Rate'].mean():.2%}" if len(click_rows) else "N/A",
          help="Chỉ tính trên các bài có dữ liệu click (Facebook, LinkedIn, TikTok)")
k5.metric("Tỷ lệ bài viral", f"{f['Is_Viral'].mean():.1%}",
          help="Viral = top 10% lượt xem của toàn bộ dữ liệu")

st.divider()

# ---------- Các tab ----------
tab1, tab2, tab3, tab4 = st.tabs(["Nền tảng & định dạng", "Xu hướng & thời điểm",
                                  "Quảng cáo", "Dữ liệu"])

# ===== Tab 1 =====
with tab1:
    c1, c2 = st.columns(2)

    plat = (f.groupby("Platform")
              .agg(rate=("Engagement_Rate", "mean"), posts=("Post_ID", "count"))
              .reset_index().sort_values("rate", ascending=False))
    fig = px.bar(plat, x="Platform", y="rate", text=plat["rate"].map("{:.1%}".format),
                 hover_data={"posts": True, "rate": ":.3f"},
                 labels={"rate": "Engagement Rate TB", "Platform": "Nền tảng", "posts": "Số bài"},
                 title="Engagement Rate theo nền tảng")
    fig.update_yaxes(range=[0, plat["rate"].max() * 1.2], tickformat=".0%")
    c1.plotly_chart(fig, use_container_width=True)

    pt = (f.groupby("Post_Type")
            .agg(rate=("Engagement_Rate", "mean"), posts=("Post_ID", "count"))
            .reset_index().sort_values("rate"))
    pt["Cỡ mẫu"] = pt["posts"].apply(lambda n: "Ít bài (<100)" if n < 100 else "Đủ bài")
    fig = px.bar(pt, x="rate", y="Post_Type", orientation="h", color="Cỡ mẫu",
                 color_discrete_map={"Đủ bài": "#4C78A8", "Ít bài (<100)": "#BBBBBB"},
                 text=pt["rate"].map("{:.1%}".format),
                 hover_data={"posts": True, "rate": ":.3f"},
                 labels={"rate": "Engagement Rate TB", "Post_Type": "Định dạng", "posts": "Số bài"},
                 title="Engagement Rate theo định dạng")
    fig.update_xaxes(range=[0, pt["rate"].max() * 1.25], tickformat=".0%")
    c2.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    cat = (f.groupby("Content_Category")["Engagement_Rate"].mean()
             .reset_index().sort_values("Engagement_Rate"))
    fig = px.bar(cat, x="Engagement_Rate", y="Content_Category", orientation="h",
                 labels={"Engagement_Rate": "Engagement Rate TB", "Content_Category": "Chủ đề"},
                 title="Engagement Rate theo chủ đề nội dung")
    fig.update_xaxes(tickformat=".0%")
    c3.plotly_chart(fig, use_container_width=True)

    reg = (f.groupby("Region")["Views"].sum().div(1e6)
             .reset_index().sort_values("Views"))
    fig = px.bar(reg, x="Views", y="Region", orientation="h",
                 labels={"Views": "Lượt xem (triệu)", "Region": "Quốc gia"},
                 title="Tổng lượt xem theo quốc gia")
    c4.plotly_chart(fig, use_container_width=True)

# ===== Tab 2 =====
with tab2:
    m = (f[f["YearMonth"] != PARTIAL_MONTH]
         .groupby("YearMonth")
         .agg(views=("Views", "sum"), rate=("Engagement_Rate", "mean"))
         .reset_index())
    m["views_m"] = m["views"] / 1e6
    c1, c2 = st.columns(2)
    fig = px.line(m, x="YearMonth", y="views_m", markers=True,
                  labels={"views_m": "Lượt xem (triệu)", "YearMonth": "Tháng"},
                  title="Tổng lượt xem theo tháng")
    c1.plotly_chart(fig, use_container_width=True)

    fig = px.line(m, x="YearMonth", y="rate", markers=True,
                  labels={"rate": "Engagement Rate TB", "YearMonth": "Tháng"},
                  title="Engagement Rate theo tháng")
    fig.update_yaxes(tickformat=".1%")
    c2.plotly_chart(fig, use_container_width=True)
    st.caption(f"Tháng {PARTIAL_MONTH} chỉ có vài bài (dữ liệu dừng ngày 01/05) nên không hiển thị.")

    heat = f.pivot_table(index="Weekday", columns="Post_Hour",
                         values="Engagement_Rate", aggfunc="mean", observed=True)
    fig = px.imshow(heat, aspect="auto", color_continuous_scale="YlGnBu",
                    labels={"x": "Giờ đăng", "y": "Thứ", "color": "Engagement Rate TB"},
                    title="Engagement Rate theo thứ và giờ đăng")
    st.plotly_chart(fig, use_container_width=True)

# ===== Tab 3 =====
with tab3:
    c1, c2 = st.columns(2)
    fig = px.box(f, x="Content_Type", y="Engagement_Rate", color="Content_Type",
                 labels={"Content_Type": "Loại nội dung", "Engagement_Rate": "Engagement Rate"},
                 title="Engagement Rate: Organic vs Sponsored")
    fig.update_layout(showlegend=False)
    c1.plotly_chart(fig, use_container_width=True)

    if len(click_rows):
        fig = px.box(click_rows, x="Content_Type", y="Click_Through_Rate", color="Content_Type",
                     labels={"Content_Type": "Loại nội dung", "Click_Through_Rate": "CTR"},
                     title="CTR: Organic vs Sponsored (bài có dữ liệu click)")
        fig.update_layout(showlegend=False)
        c2.plotly_chart(fig, use_container_width=True)

        ctr_p = (click_rows.groupby("Platform")["Click_Through_Rate"].mean()
                 .reset_index().sort_values("Click_Through_Rate", ascending=False))
        fig = px.bar(ctr_p, x="Platform", y="Click_Through_Rate",
                     text=ctr_p["Click_Through_Rate"].map("{:.2%}".format),
                     labels={"Click_Through_Rate": "CTR TB", "Platform": "Nền tảng"},
                     title="CTR theo nền tảng (chỉ nền tảng có dữ liệu click)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        c2.info("Bộ lọc hiện tại không có bài nào có dữ liệu click "
                "(chỉ Facebook, LinkedIn, TikTok có dữ liệu này).")

# ===== Tab 4 =====
with tab4:
    st.write(f"Đang hiển thị **{len(f):,}** / {len(df):,} dòng")
    show_cols = ["Post_ID", "Platform", "Content_Type", "Content_Category", "Post_Type",
                 "Region", "Post_Date", "Post_Hour", "Views", "Engagement",
                 "Engagement_Rate", "Click_Through_Rate"]
    st.dataframe(f[show_cols], use_container_width=True, height=420)
    st.download_button("⬇️ Tải dữ liệu đã lọc (CSV)",
                       f[show_cols].to_csv(index=False).encode("utf-8-sig"),
                       file_name="filtered_data.csv", mime="text/csv")
