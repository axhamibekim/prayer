
import os
import base64
import json
import pandas as pd
import requests
import streamlit as st
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(page_title="Namaz Tracker (5 Vakte)", layout="centered")

# Persist selected date
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

DATA_FILE = "prayer_log.csv"
PRAYERS = ["Fajr (Sabah)", "Dhuhr (Dreka)", "Asr (Ikindia)", "Maghrib (Aksham)", "Isha (Jacia)"]

# ----------- GitHub helpers -----------
def _gh_enabled():
    required = ["GITHUB_TOKEN", "GH_OWNER", "GH_REPO", "GH_BRANCH", "GH_CSV_PATH"]
    return all(k in st.secrets for k in required)

def _gh_headers():
    return {
        "Authorization": f"token {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }

def _gh_repo_info():
    owner = st.secrets["GH_OWNER"]
    repo = st.secrets["GH_REPO"]
    branch = st.secrets.get("GH_BRANCH", "main")
    path = st.secrets.get("GH_CSV_PATH", "prayer_log.csv")
    return owner, repo, branch, path

def github_get_file_sha():
    owner, repo, branch, path = _gh_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    r = requests.get(url, headers=_gh_headers(), timeout=30)
    if r.status_code == 200:
        j = r.json()
        return j.get("sha"), j.get("content"), j.get("encoding")
    return None, None, None

def github_pull_csv_to_local():
    sha, content_b64, enc = github_get_file_sha()
    if not content_b64:
        return False
    try:
        raw = base64.b64decode(content_b64)
        with open(DATA_FILE, "wb") as f:
            f.write(raw)
        return True
    except Exception as e:
        st.warning(f"GitHub pull error: {e}")
        return False

def github_upsert_csv(local_csv_bytes, commit_message="Update prayer_log.csv"):
    owner, repo, branch, path = _gh_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    sha, _, _ = github_get_file_sha()
    payload = {
        "message": commit_message,
        "content": base64.b64encode(local_csv_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=_gh_headers(), data=json.dumps(payload), timeout=30)
    if r.status_code not in (200, 201):
        st.warning(f"GitHub save failed: {r.status_code} - {r.text}")
        return False
    st.toast("✅ U ruajt në GitHub", icon="✅")
    return True

# ----------- Data helpers -----------
def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        if _gh_enabled():
            pulled = github_pull_csv_to_local()
            if pulled and os.path.exists(DATA_FILE):
                return
        df = pd.DataFrame(columns=["date"] + PRAYERS)
        df.to_csv(DATA_FILE, index=False)

def load_data():
    ensure_data_file()
    df = pd.read_csv(DATA_FILE)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date.astype(str)
    return df

def save_day(selected_date: date, marks: dict):
    df = load_data()
    sdate = selected_date.strftime("%Y-%m-%d")
    row = {"date": sdate}
    row.update({p: int(marks.get(p, False)) for p in PRAYERS})
    if (df["date"] == sdate).any():
        df.loc[df["date"] == sdate, PRAYERS] = [row[p] for p in PRAYERS]
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.sort_values("date")
    df.to_csv(DATA_FILE, index=False)
    if _gh_enabled():
        try:
            github_upsert_csv(df.to_csv(index=False).encode("utf-8"), commit_message=f"update {sdate}")
        except Exception as e:
            st.warning(f"GitHub error: {e}")
    return df

def get_marks_for_date(df, selected_date: date):
    sdate = selected_date.strftime("%Y-%m-%d")
    row = df[df["date"] == sdate]
    if row.empty:
        return {p: False for p in PRAYERS}
    r = row.iloc[0]
    return {p: bool(int(r.get(p, 0))) for p in PRAYERS}

def compute_stats(df, window_days=30):
    if df.empty:
        return {"days_tracked": 0, "avg_perc": 0.0, "best_streak": 0, "current_streak": 0}
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    cutoff = date.today() - timedelta(days=window_days - 1)
    window = df[df["date"] >= cutoff]
    days_tracked = window.shape[0]
    if days_tracked == 0:
        return {"days_tracked": 0, "avg_perc": 0.0, "best_streak": 0, "current_streak": 0}
    window["completed"] = window[PRAYERS].astype(int).sum(axis=1)
    window["perc"] = (window["completed"] / len(PRAYERS)) * 100.0
    avg_perc = float(window["perc"].mean())
    days = sorted(window["date"].tolist())
    best_streak = 0
    current_streak = 0
    last_day = None
    for d in days:
        full = int(window[window["date"] == d]["completed"].iloc[0]) == len(PRAYERS)
        if full:
            if last_day is None or (d - last_day).days == 1:
                current_streak += 1
            else:
                current_streak = 1
            best_streak = max(best_streak, current_streak)
        else:
            current_streak = 0
        last_day = d
    return {
        "days_tracked": int(days_tracked),
        "avg_perc": round(avg_perc, 1),
        "best_streak": int(best_streak),
        "current_streak": int(current_streak),
    }

# ----------- Sidebar nav -----------
view = st.sidebar.radio("Zgjidh faqen", ["🕌 Namaz Tracker", "📊 Raport Mujor"])

# ----------- Page 1: Namaz Tracker -----------
if view == "🕌 Namaz Tracker":
    st.title("🕌 Namaz Tracker — 5 Vakte")
    st.caption("Shëno vaktet e ditës dhe shiko progresin për 30 ditë.")

    df = load_data()
    col_date, col_tools = st.columns([2, 1])
    with col_date:
        selected_date = st.date_input("Data", value=st.session_state.selected_date, format="YYYY-MM-DD")
        st.session_state.selected_date = selected_date
    with col_tools:
        st.write("")
        st.write("")
        if st.button("Shko në sot"):
            st.session_state.selected_date = date.today()
            selected_date = st.session_state.selected_date

    marks_today = get_marks_for_date(df, selected_date)

    st.subheader("Vaktet e ditës")
    c1, c2 = st.columns(2)
    with c1:
        fajr = st.checkbox("Fajr (Sabah)", value=marks_today["Fajr (Sabah)"])
        dhuhr = st.checkbox("Dhuhr (Dreka)", value=marks_today["Dhuhr (Dreka)"])
        asr = st.checkbox("Asr (Ikindia)", value=marks_today["Asr (Ikindia)"])
    with c2:
        maghrib = st.checkbox("Maghrib (Aksham)", value=marks_today["Maghrib (Aksham)"])
        isha = st.checkbox("Isha (Jacia)", value=marks_today["Isha (Jacia)"])

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("✅ Shëno ditën"):
            updated = {"Fajr (Sabah)": fajr, "Dhuhr (Dreka)": dhuhr, "Asr (Ikindia)": asr, "Maghrib (Aksham)": maghrib, "Isha (Jacia)": isha}
            df = save_day(selected_date, updated)
            st.success("U ruajt me sukses.")
    with colB:
        if st.button("✓ Shëno të gjitha"):
            updated = {p: True for p in PRAYERS}
            df = save_day(selected_date, updated)
            st.success("U shënuan të gjitha ✓.")
    with colC:
        if st.button("🧹 Pastro ditën"):
            updated = {p: False for p in PRAYERS}
            df = save_day(selected_date, updated)
            st.info("U hoqën shënimet.")

# ----------- Page 2: Raport Mujor -----------
elif view == "📊 Raport Mujor":
    st.title("📊 Raport Mujor")
    df = load_data()
    if df.empty:
        st.info("Nuk ka të dhëna për raport.")
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        last_30 = df[df["date"] >= (date.today() - timedelta(days=29))].copy()
        last_30["completed"] = last_30[PRAYERS].astype(int).sum(axis=1)
        last_30["perc"] = (last_30["completed"] / len(PRAYERS)) * 100.0

        avg_perc = round(last_30["perc"].mean(), 1)
        full_days = int((last_30["completed"] == len(PRAYERS)).sum())

        c1, c2 = st.columns(2)
        c1.metric("Mesatarja mujore", f"{avg_perc}%")
        c2.metric("Ditë me 5/5 vakte", full_days)

        fig, ax = plt.subplots()
        ax.plot(last_30["date"], last_30["perc"], marker="o")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Përqindje ditore")
        ax.set_title("Progresi 30-ditor")
        st.pyplot(fig)

        st.dataframe(last_30.sort_values("date", ascending=False), use_container_width=True)
