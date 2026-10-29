import pandas as pd
import streamlit as st

from core.project import PROJECT
from core.resources import (MIME, READINGS, REVISION_NOTES, VIDEO_ATTRIBUTION, VIDEOS,
                            list_class_materials)
from core.ui import footer, page_header

page_header(":material/groups:", "Team & learning resources",
            f"{PROJECT['course']}, {PROJECT['activity']} · {PROJECT['institute']}", kicker="About")

# --- Team -----------------------------------------------------------------------------

st.header("Team", divider="gray")
cols = st.columns(len(PROJECT["members"]))
for col, (name, prn) in zip(cols, PROJECT["members"]):
    with col.container(border=True, height="stretch"):
        st.markdown(f"**:material/person: {name}**")
        st.caption(f"PRN {prn}")
if PROJECT.get("guide"):
    st.markdown(f":material/school: **Project guide:** {PROJECT['guide']}")

# --- Revision notes -------------------------------------------------------------------------

st.header("Quick revision notes", divider="gray")
st.caption("Written for this project from the course textbook (see References). One idea per card.")
note_cols = st.columns(2)
for k, (term, text) in enumerate(REVISION_NOTES):
    with note_cols[k % 2].container(border=True, height="stretch"):
        st.markdown(f"**{term}**")
        st.write(text)

# --- Videos -----------------------------------------------------------------------------------

st.header("Lecture videos", divider="gray")
videos = pd.DataFrame([{"Topic": topic, "Title": title, "Channel": channel, "Link": url}
                       for title, channel, url, topic in VIDEOS])
st.dataframe(videos, hide_index=True, width="stretch",
             column_config={"Link": st.column_config.LinkColumn(display_text="Open on YouTube")})
pick = st.selectbox("Watch here", range(len(VIDEOS)), format_func=lambda i: f"{VIDEOS[i][3]}: {VIDEOS[i][0]}")
st.video(VIDEOS[pick][2])
st.caption(f"Videos are third-party content, shown via YouTube embeds and owned by their channels. "
           f"{VIDEO_ATTRIBUTION}")

# --- Reading --------------------------------------------------------------------------------------

st.header("References", divider="gray")
st.dataframe(pd.DataFrame([{"Reference": cite, "Covers": what, "Link": url} for cite, url, what in READINGS]),
             hide_index=True, width="stretch",
             column_config={"Reference": st.column_config.TextColumn(width="large"),
                            "Link": st.column_config.LinkColumn(display_text="Open")})
st.caption("Tanenbaum's book has no free online copy, so no link is given.")

# --- Class materials --------------------------------------------------------------------------------

st.header("Class materials", divider="gray")
files = list_class_materials()
if not files:
    st.info(
        "**No class materials are included yet.** To add instructor-authorized notes or slides, put the "
        "PDF, PPT or PPTX files in the `class_notes/` folder of the repository. They will be listed here "
        "for download. Only add files you have permission to share, because the repository is public.",
        icon=":material/folder_open:",
    )
else:
    st.caption("Instructor-authorized files placed in `class_notes/`.")
    for f in files:
        with st.container(border=True, horizontal=True, vertical_alignment="center"):
            st.markdown(f":material/description: **{f.name}** · {f.stat().st_size / 1024:,.0f} KB")
            st.download_button("Download", f.read_bytes(), f.name, MIME[f.suffix.lower()],
                               icon=":material/download:", key=f"dl_{f.name}")

st.header("Attribution", divider="gray")
st.markdown(
    "- Algorithms, explanations, games and code in this dashboard are original to this project.\n"
    "- Feature ideas (ignorance module, games, team page, video list) were taken from the team's earlier "
    "prototype, [Viveksanap18/Deadlock](https://github.com/Viveksanap18/Deadlock). "
    "No code was copied from it.\n"
    "- Textbook concepts follow Silberschatz, Galvin & Gagne, *Operating System Concepts*, 10th ed.\n"
    "- Videos belong to their YouTube channels, named above."
)

footer()
