
# Namaz Tracker — 5 Vakte (GitHub Sync)

Ky app me Streamlit lejon shënimin e 5 vakteve dhe ruan `prayer_log.csv` lokalisht **dhe** në GitHub (nëse konfigurohet GitHub API).
Funksionon në PC dhe në Streamlit Cloud.

## 1) Files
- `app.py` → aplikacioni Streamlit
- `requirements.txt` → varësitë
- (ops.) `README.md`

## 2) Përdorimi lokalisht
```bash
pip install -r requirements.txt
streamlit run app.py
```
CSV ruhet te `./prayer_log.csv`. Nëse vendos sekrete si më poshtë (p.sh. duke përdorur Streamlit Cloud), do të bëjë edhe commit në GitHub.

## 3) GitHub PAT & Secrets (për Streamlit Cloud)
Krijo një **Personal Access Token (classic)** me scope `repo`. Pastaj te **Streamlit → Settings → Secrets** vendos:

```toml
GITHUB_TOKEN = "PUT_YOUR_TOKEN_HERE"
GH_OWNER = "YourGitHubUsername"
GH_REPO = "namaz-tracker"
GH_BRANCH = "main"
GH_CSV_PATH = "prayer_log.csv"
```

## 4) Deploy në Streamlit Cloud
- Krijo një repo p.sh. `namaz-tracker`, ngarko `app.py` dhe `requirements.txt`.
- Streamlit Cloud → New app → Zgjidh repo/branch/fajlin `app.py`.
- Te **Secrets** vendos vlerat si më sipër.
- Sa herë shtyp “Shëno ditën”, CSV ruhet lokalisht (kur xhiron nga PC) **dhe** bëhet commit në repo nëse secrets janë të vendosura.

## 5) Sync manual
Në sidebar ke butona:
- **Push në GitHub (manual)** → dërgon `prayer_log.csv` në repo me commit.
- **Sync nga GitHub → lokal** → shkarkon versionin aktual nga repo dhe e ruan në disk.

> Shënim: Streamlit Cloud nuk ka storage të përhershme; prandaj ruajtja në GitHub është mënyra e rekomanduar për persistencë.
