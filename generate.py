import os
from openai import OpenAI
from dotenv import load_dotenv

# Charger les variables du fichier .env
load_dotenv()

# Récupérer la clé API depuis la variable d'environnement
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_fiche(subject):
    prompt = f"""
    Tu es un professeur de lycée. Crée une fiche de révision claire et concise sur le sujet suivant : {subject}.
    Structure :
    - Titre
    - 3 à 5 sous-titres avec explications
    - Définitions clés
    - Dates / formules importantes
    - Résumé final en 3 phrases
    Réponds en Markdown, en français.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    sujet = input("Entre ton sujet de fiche : ")
    print("\n=== Fiche générée ===\n")
    fiche = generate_fiche(sujet)
    print(fiche)

    os.makedirs("examples", exist_ok=True)
    filename = f"examples/fiche_{sujet.replace(' ', '_')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(fiche)
    print(f"\nFiche sauvegardée dans {filename}")

