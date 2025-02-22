import sys
import gurobipy as gp
from gurobipy import GRB

# Fonction pour lire les données d'entrée à partir d'un fichier
def read_input(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Lire le nombre de photos
    num_photos = int(lines[0].strip())
    photos = []

    # Lire les détails de chaque photo
    for i in range(1, num_photos + 1):
        parts = lines[i].strip().split()
        orientation = parts[0]  # Orientation de la photo ('H' pour horizontale, 'V' pour verticale)
        num_tags = int(parts[1])  # Nombre de tags associés à la photo
        tags = parts[2:2 + num_tags]  # Liste des tags
        photos.append((orientation, tags, i - 1))  # Ajouter la photo avec son index original

    return photos

# Fonction pour calculer le score de transition entre deux ensembles de tags
def transition_score(tags1, tags2):
    tags1_set = set(tags1)
    tags2_set = set(tags2)
    common_tags = len(tags1_set & tags2_set)  # Tags communs
    unique_tags1 = len(tags1_set - tags2_set)  # Tags uniques au premier ensemble
    unique_tags2 = len(tags2_set - tags1_set)  # Tags uniques au second ensemble
    return min(common_tags, unique_tags1, unique_tags2)  # Retourner le score minimum

# Fonction pour résoudre le problème du diaporama
def solve_slideshow(photos):
    model = gp.Model("Slideshow")

    # Séparer les photos horizontales et verticales
    horizontal_photos = [(i, p[1]) for i, p in enumerate(photos) if p[0] == 'H']
    vertical_photos = [(i, p[1]) for i, p in enumerate(photos) if p[0] == 'V']

    # Créer des diapositives : soit une photo horizontale, soit deux photos verticales
    slides = []
    slide_tags = []

    # Ajouter les photos horizontales comme diapositives individuelles
    for h_photo in horizontal_photos:
        slides.append([h_photo[0]])
        slide_tags.append(h_photo[1])

    # Ajouter toutes les paires possibles de photos verticales
    for i in range(len(vertical_photos)):
        for j in range(i + 1, len(vertical_photos)):
            slides.append([vertical_photos[i][0], vertical_photos[j][0]])
            combined_tags = list(set(vertical_photos[i][1] + vertical_photos[j][1]))  # Combiner les tags
            slide_tags.append(combined_tags)

    # Variables pour la sélection et l'ordre des diapositives
    x = model.addVars(len(slides), vtype=GRB.BINARY, name="slide_used")
    y = model.addVars(len(slides), len(slides), vtype=GRB.BINARY, name="transition")
    pos = model.addVars(len(slides), vtype=GRB.INTEGER, name="position")

    # Chaque photo peut être utilisée au plus une fois
    for p in range(len(photos)):
        model.addConstr(
            gp.quicksum(x[s] for s in range(len(slides)) if p in slides[s]) <= 1
        )

    # Au moins une diapositive doit être utilisée
    model.addConstr(x.sum() >= 1)

    # Contraintes de transition
    for i in range(len(slides)):
        for j in range(len(slides)):
            if i != j:
                # y[i,j] peut être 1 seulement si les deux diapositives sont utilisées
                model.addConstr(y[i, j] <= x[i])
                model.addConstr(y[i, j] <= x[j])

                # Ordre des positions pour les transitions
                model.addConstr(pos[j] >= pos[i] + 1 - len(slides) * (1 - y[i, j]))

    # Chaque diapositive peut avoir au plus un prédécesseur et un successeur
    for i in range(len(slides)):
        model.addConstr(gp.quicksum(y[i, j] for j in range(len(slides)) if j != i) <= x[i])
        model.addConstr(gp.quicksum(y[j, i] for j in range(len(slides)) if j != i) <= x[i])

    # Objectif : maximiser les scores de transition
    objective = gp.quicksum(
        transition_score(slide_tags[i], slide_tags[j]) * y[i, j]
        for i in range(len(slides))
        for j in range(len(slides))
        if i != j
    )
    model.setObjective(objective, GRB.MAXIMIZE)

    # Résoudre le modèle
    model.optimize()

    # Extraire la solution
    selected_slides = []
    for i in range(len(slides)):
        if x[i].x > 0.5:
            selected_slides.append((pos[i].x, slides[i]))

    # Trier par position
    selected_slides.sort()
    return [slide for _, slide in selected_slides]

# Fonction principale
def main():
    if len(sys.argv) != 2:
        print("Usage: python slideshow.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    photos = read_input(input_file)
    slideshow = solve_slideshow(photos)

    # Écrire la solution dans un fichier
    with open('slideshow.sol', 'w') as file:
        file.write(f"{len(slideshow)}\n")
        for slide in slideshow:
            file.write(f"{' '.join(map(str, slide))}\n")

if __name__ == "__main__":
    main()