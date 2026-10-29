import streamlit as st

from core.games import ROUNDS, grade, verdict
from core.ui import banker_matrices, footer, page_header, rag_dot, vec

page_header(":material/sports_esports:", "Deadlock games",
            "Four short rounds to test yourself. Each answer locks in when you pick it and shows an "
            "explanation straight away. Replay any round to try again.", kicker="Practise")

if "game_attempt" not in st.session_state:
    st.session_state.game_attempt = {key: 0 for key in ROUNDS}
    # First answer per question, kept apart from widget state so it can't change once given.
    st.session_state.game_answers = {key: {} for key in ROUNDS}


def answers_for(key: str) -> dict:
    return st.session_state.game_answers[key]


def lock_answer(round_key: str, q, wkey: str):
    choice = st.session_state.get(wkey)
    if choice is not None:
        st.session_state.game_answers[round_key].setdefault(q.qid, q.options.index(choice))


# --- Scoreboard across all rounds ---------------------------------------------------

grades = {key: grade(qs, answers_for(key)) for key, (_, qs) in ROUNDS.items()}
total_correct = sum(g.correct for g in grades.values())
total_q = sum(g.total for g in grades.values())
total_answered = sum(g.answered for g in grades.values())
with st.container(horizontal=True):
    st.metric("Total score", f"{total_correct} / {total_q}", border=True)
    st.metric("Answered", f"{total_answered} / {total_q}", border=True)
    st.metric("Rounds complete", f"{sum(g.complete for g in grades.values())} / {len(ROUNDS)}", border=True)

key = st.segmented_control("Round", list(ROUNDS), format_func=lambda k: f"{ROUNDS[k][0]} "
                           f"({grades[k].correct}/{grades[k].total})", default="coffman", key="game_round",
                           required=True)
title, questions = ROUNDS[key]
attempt = st.session_state.game_attempt[key]
g = grades[key]

st.header(title, divider="gray")
st.progress(g.answered / g.total, text=f"{g.answered} of {g.total} answered · {g.correct} correct")

for n, q in enumerate(questions, start=1):
    wkey = f"game_{key}_{attempt}_{q.qid}"
    with st.container(border=True):
        st.markdown(f"**Q{n}.** {q.prompt}")
        fig = q.figure
        if fig.get("kind") == "banker":
            n_p = len(fig["allocation"])
            banker_matrices(fig["allocation"], fig["maximum"], fig["need"], fig["resources"], [False] * n_p)
            st.caption(f"Available = {vec(fig['available'])}")
        elif fig.get("kind") == "graph":
            st.graphviz_chart(rag_dot(fig["allocation"], fig["request"], fig["resources"],
                                      available=fig["available"], show_states=False), width="stretch")
            st.caption("Solid arrows: held. Dashed arrows: waiting for. ● held instance, ○ free instance.")
        given = answers_for(key).get(q.qid)
        if given is None:
            st.radio("Your answer", q.options, index=None, key=wkey, on_change=lock_answer,
                     args=(key, q, wkey), horizontal=len(q.options) <= 2, label_visibility="collapsed")
        else:
            st.radio("Your answer", q.options, index=given, key=f"{wkey}_locked", disabled=True,
                     horizontal=len(q.options) <= 2, label_visibility="collapsed")
            if given == q.answer:
                st.success(f"**Correct.** {q.explanation}", icon=":material/check_circle:")
            else:
                st.error(f"**Not quite. Answer: {q.options[q.answer]}.** {q.explanation}", icon=":material/close:")

if g.complete:
    (st.success if g.correct == g.total else st.info)(
        f"**Round complete: {g.correct} / {g.total} ({g.percent}%).** {verdict(g)}", icon=":material/emoji_events:")


def replay(round_key: str):
    st.session_state.game_attempt[round_key] += 1      # fresh widget keys
    st.session_state.game_answers[round_key] = {}


with st.container(horizontal=True):
    st.button("Replay this round", icon=":material/replay:", on_click=replay, args=(key,),
              type="primary" if g.complete else "secondary")
    st.button("Reset all rounds", icon=":material/restart_alt:",
              on_click=lambda: [replay(k) for k in ROUNDS])

footer()
