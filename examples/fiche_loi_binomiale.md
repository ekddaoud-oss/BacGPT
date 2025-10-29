# Fiche de Révision : Loi Binomiale

## 1. Définition de la Loi Binomiale
La loi binomiale est une loi de probabilité qui modélise le nombre de succès dans une série d'essais indépendants, chacun ayant deux issues possibles (succès ou échec). Elle est utilisée lorsque les essais sont identiques et que la probabilité de succès reste constante.

## 2. Paramètres de la Loi Binomiale
La loi binomiale est caractérisée par deux paramètres :
- **n** : le nombre d'essais (ou répétitions).
- **p** : la probabilité de succès lors d'un essai.

## 3. Fonction de Probabilité
La fonction de probabilité d'une variable aléatoire X suivant une loi binomiale est donnée par la formule :
\[ P(X = k) = \binom{n}{k} \cdot p^k \cdot (1-p)^{n-k} \]
où \( k \) est le nombre de succès souhaité, et \( \binom{n}{k} \) est le coefficient binomial.

## 4. Espérance et Variance
- **Espérance (E(X))** : \( E(X) = n \cdot p \)
- **Variance (Var(X))** : \( Var(X) = n \cdot p \cdot (1-p) \)

## 5. Applications de la Loi Binomiale
La loi binomiale est utilisée dans divers domaines tels que :
- Les jeux de hasard (ex. lancer de dés, tirage de cartes).
- Les études de marché (ex. proportion de clients satisfaits).
- Les tests de qualité (ex. nombre de produits défectueux).

---

### Définitions clés
- **Essai** : Un événement dont le résultat est incertain.
- **Succès** : L'issue favorable d'un essai.
- **Échec** : L'issue défavorable d'un essai.
- **Coefficient binomial** : \( \binom{n}{k} = \frac{n!}{k!(n-k)!} \)

### Dates / Formules importantes
- **Formule de la fonction de probabilité** : \( P(X = k) = \binom{n}{k} \cdot p^k \cdot (1-p)^{n-k} \)
- **Espérance** : \( E(X) = n \cdot p \)
- **Variance** : \( Var(X) = n \cdot p \cdot (1-p) \)

---

### Résumé final
La loi binomiale est une loi de probabilité essentielle qui modélise des situations avec des essais indépendants à deux issues. Elle est définie par ses paramètres n et p, et permet de calculer des probabilités, ainsi que d'obtenir l'espérance et la variance d'une variable aléatoire.