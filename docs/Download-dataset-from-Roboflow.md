# Downloading datasets from Roboflow

1. Create a virtual environment and install the `roboflow` package:

```bash
python -m venv .venv.ml
source .venv.ml/bin/activate
pip install roboflow
```

or by using `uv`:

```bash
uv venv .venv.ml --seed
source .venv.ml/bin/activate
uv pip install roboflow
```

2. Login to the Roboflow CLI:

```bash
roboflow login
```

3. It will provide a link to open in the browser. Open the link and copy the API key provided into the terminal.

4. Download the dataset using the following command:

```bash
roboflow download -f yolov11 -l path/to/dataset/output tcddthesis/merged-ph-tcd-1-bbox-cvat/[version_number_here]
```
