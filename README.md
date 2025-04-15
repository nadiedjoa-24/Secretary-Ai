# Installation et Configuration de llama.cpp

## 1. Cloner le dépôt `llama.cpp`

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
```

Vérifiez la version de `nvcc` :

```bash
nvcc --version
```

Si aucune sortie n'est affichée, redéfinir les variables locales :

```bash
export PATH=/usr/local/cuda-12.5/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.5/targets/x86_64-linux/lib:$LD_LIBRARY_PATH
export LIBRARY_PATH=/usr/local/cuda-12.5/targets/x86_64-linux/lib:$LIBRARY_PATH
export CUDACXX=/usr/local/cuda-12.5/bin/nvcc
```

---

## 2. Compiler `llama.cpp` avec support GPU

Nettoyez les fichiers de compilation existants :

```bash
rm -rf build
```

Générez les fichiers de compilation avec CUDA activé :

```bash
cmake -B build -DGGML_CUDA=ON 
```
si ca fonctionne pas : 
```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.5/bin/nvcc
```

Compilez le projet en utilisant tous les cœurs disponibles :

```bash
cmake --build build --config Release -j $(nproc)
```

le ` nrpoc `signifie que l'on prend tous les coeurs dispo.


---

## 3. Téléchargement du Modèle Mistral 7B GGUF

Téléchargez le modèle Mistral 7B quantisé :

```bash
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf -P models/
```

Vérifiez la disponibilité du GPU :

```bash
nvidia-smi
```

Lancez Mistral 7B :

```bash
CUDA_VISIBLE_DEVICES=0 ./build/bin/llama-cli -m models/mistral-7b-instruct-v0.2.Q4_K_M.gguf --interactive --n-gpu-layers 100
```

### Explication des paramètres :
- `CUDA_VISIBLE_DEVICES=0` → Force l'utilisation du GPU 0.
- `-m models/mistral-7b-instruct-v0.2.Q4_K_M.gguf` → Charge le modèle GGUF.
- `--interactive` → Active le mode conversationnel.
- `--n-gpu-layers 100` → Charge 100 couches du modèle sur GPU (ajuster si VRAM insuffisante).

---

## 4. Optimisation des Performances

### Limiter les threads CPU (`-t 16`)

```bash
CUDA_VISIBLE_DEVICES=0 ./build/bin/llama-cli -m models/mistral-7b-instruct-v0.2.Q4_K_M.gguf --interactive --n-gpu-layers 100 -t 16
```
---

### Réduire la taille du contexte (`--ctx-size 2048`)

```bash
CUDA_VISIBLE_DEVICES=0 ./build/bin/llama-cli -m models/mistral-7b-instruct-v0.2.Q4_K_M.gguf --interactive --n-gpu-layers 100 -t 16 --ctx-size 2048
```


---

### Optimiser le chargement (`--no-mmap --no-warmup`)

- `--no-mmap` → Désactive le mappage mémoire, accélère le chargement.
- `--no-warmup` → Désactive l'échauffement initial, réduit l'attente.

---



## 5. Charger les modèles en local et les executer sur gpu à partir de packages python

- Pour charger des modèles depuis hugging face directement depuis hugging face, utiliser le package `transformer`.
- Pour charger les modèles depuis llama.cpp, installer le package sur la ligne de commande en spécifiant l'installation du package sur gpu : 

```bash
pip install llama-cpp-python[cuda]
```
ou
```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```


## 6. API de networking pour exécuter les modèles sur gpu à distance 

- Exécuter le script `serveur.py` sur le gpu (il faut cloner le repo pour avoir accès à ai_controller).
- On peut ensuite soit utiliser la ligne de commande avec `CURL`en méthode `POST` ou exécuter le script `client.py` pour intéragir.
- La classe `Client` permet de l'intégrer à d'autres scripts.
