# app.py — IA Fiches (version robuste, sans erreurs)
import os
import re
import json
import string
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import markdown2

# -----------------------
# Configuration & init
# -----------------------
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OPENAI_API_KEY non définie. Crée un fichier .env contenant :\nOPENAI_API_KEY=sk-...")
    st.stop()

client = OpenAI(api_key=API_KEY)

st.set_page_config(page_title="IA Fiches", page_icon="🧠", layout="wide")
st.title("🧠 IA Fiches — Générateur de fiches + quiz")
st.write("Entre un sujet → l'IA génère une fiche et un quiz. Réponds puis clique sur « Vérifier toutes les réponses ».")
st.markdown("---")

# -----------------------
# Utilitaires
# -----------------------
def clean_json_text(raw: str) -> str:
    """
    Tente d'isoler et nettoyer un bloc JSON renvoyé par le modèle.
    Échappe les backslashes LaTeX et retire retours-lignes gênants.
    """
    if raw is None:
        return ""
    s = raw.strip()
    # Remplacer retours de ligne par espaces (éviter JSON brisé)
    s = s.replace("\r", " ").replace("\n", " ")
    # Isoler premier tableau [] ou premier objet {}
    if "[" in s and "]" in s:
        s = s[s.find("["): s.rfind("]") + 1]
    elif "{" in s and "}" in s:
        s = s[s.find("{"): s.rfind("}") + 1]
    # Échapper les backslashes devant parenthèses/brackets/braces (LaTeX) pour ne pas casser JSON
    s = re.sub(r'\\([(){}\[\]])', r'\\\\\1', s)
    # Nettoyer guillemets mal échappés
    s = s.replace('\\"', '"').replace("\\'", "'")
    return s.strip()

def normalize_text(s: str) -> str:
    """Normalise chaîne : minuscules, espaces simples, enlève ponctuation ASCII."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    # retirer ponctuation ASCII (ne touche pas aux accents)
    s = s.translate(str.maketrans("", "", string.punctuation))
    return s.strip()

def extract_label_and_text(opt: str):
    """
    Si option commence par 'A) texte' ou 'A. texte' ou 'A - texte' ou 'A: texte',
    retourne (label, text). Sinon (None, opt).
    """
    if opt is None:
        return None, ""
    m = re.match(r'^\s*([A-Da-d])\s*[\)\.\-:\s]+\s*(.*)$', opt)
    if m:
        return m.group(1).upper(), m.group(2).strip()
    return None, opt.strip()

def resolve_correct_text(q: dict):
    """
    A partir du champ q['correct'] et q['options'], retourne la version texte "correct_text"
    correspondant à la bonne réponse (utile pour comparer avec la sélection de l'utilisateur).
    """
    correct_raw = str(q.get("correct", "")).strip()
    # si correct_raw est une lettre seule
    if re.fullmatch(r'^[A-Da-d]$', correct_raw):
        letter = correct_raw.upper()
        idx = ord(letter) - ord('A')
        options = q.get("options", [])
        if 0 <= idx < len(options):
            _, text = extract_label_and_text(options[idx])
            return text
        else:
            return ""
    # si correct_raw = "B) texte" ou "B. texte"
    m = re.match(r'^\s*([A-Da-d])\s*[\)\.\-:\s]+\s*(.*)$', correct_raw)
    if m:
        letter = m.group(1).upper()
        text = m.group(2).strip()
        # prefer text, but if empty, try options mapping
        if text:
            return text
        else:
            idx = ord(letter) - ord('A')
            options = q.get("options", [])
            if 0 <= idx < len(options):
                _, t2 = extract_label_and_text(options[idx])
                return t2
            return ""
    # sinon, assume correct_raw is the full text
    return correct_raw

# -----------------------
# Requêtes OpenAI
# -----------------------
def request_fiche(subject: str) -> str:
    prompt = f"""
Tu es un professeur de lycée. Crée une fiche de révision claire et concise sur : {subject}.
Structure :
- Titre
- 3 à 5 sous-titres courts avec explications
- Définitions clés
- Dates / formules importantes
- Résumé final en 2-3 phrases
Réponds en Markdown, en français.
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
    )
    return resp.choices[0].message.content

def request_quiz_from_fiche(fiche_text: str, subject: str) -> list:
    prompt = f"""
À partir de cette fiche sur "{subject}", crée un quiz de 5 questions à choix multiples.
Réponds **uniquement** par un tableau JSON (liste) d'objets au format EXACT suivant :
[
  {{
    "question": "Texte de la question",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": "B",
    "explanation": "Courte explication"
  }},
  ...
]
⚠️ NE mets aucun texte avant ni après le JSON. NE fournis pas de formules LaTeX dans les valeurs.
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": fiche_text},
            {"role": "user", "content": prompt}
        ],
        temperature=0.25,
    )
    raw = resp.choices[0].message.content
    cleaned = clean_json_text(raw)
    try:
        data = json.loads(cleaned)
    except Exception as e:
        # remonter erreur claire + afficher réponse brute dans UI si nécessaire
        raise RuntimeError(f"Impossible de parser le JSON renvoyé par le modèle.\nErreur: {e}\n\nRéponse brute:\n{raw}")
    # validation simple
    validated = []
    for item in data:
        if not all(k in item for k in ("question", "options", "correct", "explanation")):
            continue
        if not isinstance(item["options"], list) or len(item["options"]) != 4:
            continue
        validated.append(item)
    if not validated:
        raise RuntimeError(f"Le JSON est valide mais aucun item correct. Réponse brute:\n{raw}")
    return validated

# -----------------------
# session_state init
# -----------------------
if "fiche_md" not in st.session_state:
    st.session_state.fiche_md = None
if "fiche_subject" not in st.session_state:
    st.session_state.fiche_subject = None
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "answers" not in st.session_state:
    st.session_state.answers = {}   # keys: "q1".."qN" -> selected option (string)
if "results" not in st.session_state:
    st.session_state.results = None

# -----------------------
# UI : génération (col layout)
# -----------------------
c1, c2 = st.columns([2, 1])

with c1:
    subject = st.text_input("📘 Entre ton sujet de cours :", value=st.session_state.fiche_subject or "", placeholder="Ex: Les lois de Newton", key="input_subject")
    generate_btn = st.button("✨ Générer la fiche et le quiz", key="generate_btn")
    reset_btn = st.button("♻ Réinitialiser tout", key="reset_btn")

    if reset_btn:
        st.session_state.fiche_md = None
        st.session_state.fiche_subject = None
        st.session_state.quiz = None
        st.session_state.answers = {}
        st.session_state.results = None
        st.experimental_rerun()

    if generate_btn:
        if not subject or not subject.strip():
            st.warning("⚠️ Entre un sujet valide.")
        else:
            try:
                with st.spinner("✏️ Génération de la fiche..."):
                    fiche = request_fiche(subject)
                    st.session_state.fiche_md = fiche
                    st.session_state.fiche_subject = subject
                    # sauvegarder fiche
                    os.makedirs("examples", exist_ok=True)
                    safe_name = subject.replace("/", "-").replace(" ", "_")
                    with open(f"examples/fiche_{safe_name}.md", "w", encoding="utf-8") as f:
                        f.write(fiche)
                st.success("✅ Fiche générée et sauvegardée.")
                with st.spinner("🧩 Génération du quiz..."):
                    quiz = request_quiz_from_fiche(st.session_state.fiche_md, subject)
                    st.session_state.quiz = quiz
                    # initialiser réponses si pas déjà présentes
                    for i in range(len(quiz)):
                        key = f"q{i+1}"
                        if key not in st.session_state.answers:
                            st.session_state.answers[key] = "-- Choisir --"
                    # sauvegarder quiz
                    with open(f"examples/quiz_{safe_name}.json", "w", encoding="utf-8") as f:
                        json.dump(quiz, f, ensure_ascii=False, indent=2)
                st.success("✅ Quiz généré et sauvegardé.")
            except Exception as e:
                st.error("❌ Erreur pendant la génération.")
                st.exception(e)

with c2:
    st.markdown("### ⚙️ Statut")
    if st.session_state.fiche_md:
        st.write(f"Fiche pour : **{st.session_state.fiche_subject}**")
    else:
        st.write("Aucune fiche générée.")
    if st.session_state.quiz:
        st.write(f"Quiz chargé ({len(st.session_state.quiz)} questions)")
    else:
        st.write("Aucun quiz chargé.")

st.markdown("---")

# -----------------------
# UI : afficher fiche si existante
# -----------------------
if st.session_state.fiche_md:
    st.subheader("📄 Fiche générée")
    st.markdown(markdown2.markdown(st.session_state.fiche_md), unsafe_allow_html=True)
    st.info(f"Fiche sauvegardée dans : examples/fiche_{st.session_state.fiche_subject.replace(' ','_')}.md")
else:
    st.info("Génère d'abord une fiche pour obtenir le quiz.")

st.markdown("---")

# -----------------------
# UI : Quiz interactif
# -----------------------
if st.session_state.quiz:
    st.subheader("🎯 Quiz interactif")
    # Affichage questions et selectboxes — chaque widget a une key unique
    for i, q in enumerate(st.session_state.quiz, start=1):
        st.markdown(f"**Q{i}. {q['question']}**")
        key = f"q{i}"
        # ajouter placeholder en début
        options = ["-- Choisir --"] + q["options"]
        current = st.session_state.answers.get(key, "-- Choisir --")
        # safe index (current is guaranteed to be in options because we set it)
        try:
            idx = options.index(current)
        except ValueError:
            idx = 0
        # selectbox with unique key
        selection = st.selectbox("", options, index=idx, key=f"select_{i}")
        # store normalized selection (we keep original text)
        st.session_state.answers[key] = selection
        st.write("")

    # bouton unique pour vérifier tous les résultats (key unique)
    if st.button("✅ Vérifier toutes les réponses", key="verify_all"):
        score = 0
        results = {}
        for i, q in enumerate(st.session_state.quiz, start=1):
            key = f"q{i}"
            user = st.session_state.answers.get(key, "-- Choisir --")
            # resolved correct text (text form)
            correct_text = resolve_correct_text(q).strip()
            # normalize and compare robustly
            user_label, user_text = extract_label_and_text(user)
            if user_text is None:
                user_text = ""
            normalized_user = normalize_text(user_text)
            normalized_correct = normalize_text(correct_text)
            ok = False
            if user == "-- Choisir --":
                ok = False
            else:
                if normalized_user and normalized_correct and normalized_user == normalized_correct:
                    ok = True
                else:
                    # try letter compare: if q['correct'] is a letter or contains a letter, compare labels
                    c = str(q.get("correct","")).strip()
                    m = re.match(r'^\s*([A-Da-d])\s*[\)\.\-:\s]?', c)
                    if m:
                        corr_letter = m.group(1).upper()
                        # try to derive user's letter from their option (if they selected "A) text" or similar)
                        u_letter, _ = extract_label_and_text(user)
                        if u_letter and u_letter == corr_letter:
                            ok = True
                        else:
                            # if user selected text, compare it to option at index of corr_letter
                            idx = ord(corr_letter) - ord('A')
                            opts = q.get("options", [])
                            if 0 <= idx < len(opts):
                                _, opt_text = extract_label_and_text(opts[idx])
                                if normalize_text(opt_text) == normalized_user:
                                    ok = True
                    else:
                        # fallback: check if user's text is substring of correct or vice-versa
                        if normalized_user in normalized_correct or normalized_correct in normalized_user:
                            ok = True

            results[i] = {
                "user": user,
                "correct_raw": q.get("correct",""),
                "correct_text": correct_text,
                "ok": ok,
                "explanation": q.get("explanation", "")
            }
            if ok:
                score += 1

        st.session_state.results = {"score": score, "details": results}

    # Afficher résultats si notés
    if st.session_state.results:
        res = st.session_state.results
        st.write("---")
        st.success(f"### 🧮 Score : {res['score']}/{len(st.session_state.quiz)}")
        st.progress(res['score'] / len(st.session_state.quiz))
        for i in range(1, len(st.session_state.quiz) + 1):
            info = res["details"].get(i, {})
            ok = info.get("ok", False)
            if ok:
                st.markdown(f"✅ **Q{i}. Bonne réponse** — {info.get('correct_text')}")
            else:
                st.markdown(f"❌ **Q{i}. Mauvaise** — Ta réponse : *{info.get('user')}* — Correct : **{info.get('correct_text')}**")
                if info.get("explanation"):
                    st.info(f"💡 {info.get('explanation')}")
else:
    st.info("Aucun quiz à afficher. Génére une fiche d'abord.")

st.markdown("---")
st.caption("Prototype IA Fiches — vérifie toujours le contenu des fiches. Sauvegardes automatiques dans le dossier examples/.")






