# Développement et construction

## Lancer depuis les sources

```bash
pip install pystray pillow
python JS8toHRD.pyw
```

L'app fonctionne aussi sans `pystray`/`pillow`, mais sans icône dans la zone de notification.

## Tests

```bash
python -m unittest tests.test_core
```

Pour tester sans toucher à un vrai log, `tests/simulate.py` lance un **faux JS8Call** (API TCP)
qui envoie 4 QSO et un doublon, et un **faux HRD** (UDP) qui affiche ce qu'il reçoit :

```bash
python tests/simulate.py 2250 2350
```

Règle ensuite l'app sur ces ports (Réglages… → JS8Call 2250, HRD 2350). Un 3e argument
(en secondes) retarde le faux HRD, pour tester la mise en attente. Pour ne pas mélanger avec
tes vraies données, lance l'app avec un `APPDATA` temporaire. Dans ce cas, ajoute aussi le
dossier `site-packages` utilisateur à `PYTHONPATH` si `pystray`/`pillow` y sont installés.

## Construire l'exécutable et l'installeur

```bash
pip install pyinstaller pystray pillow
python packaging/build.py --portable --installer
```

Résultat dans `packaging/dist/` :
- `JS8toHRD/` : l'application en dossier (c'est ce que l'installeur embarque) ;
- `JS8toHRD-portable.exe` : la version un seul fichier ;
- `JS8toHRD-Setup-<version>.exe` : l'installeur (nécessite [Inno Setup 6](https://jrsoftware.org/isdl.php)).

## Publier une version

1. Mettre à jour `APP_VERSION` dans `js8hrd/core.py` et `CHANGELOG.md`.
2. Commit, puis tag : `git tag v1.2.3 && git push origin v1.2.3`.
3. GitHub Actions (`.github/workflows/build.yml`) construit l'installeur et la version portable
   et les attache à la Release.

## Captures d'écran de la doc

`packaging/screenshot.py fr|en sortie.png` capture la fenêtre (à lancer avec le simulateur).
