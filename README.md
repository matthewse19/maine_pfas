# Maine PFAS Data Web App

This repository contains the code for a web application that displays chemical PFAS (Per- and Polyfluoroalkyl Substances) data in Maine. The app allows users to explore and visualize the data interactively.

Use the interactive app by going to https://matthewse19.github.io/maine_pfas/ (Pyodide can take a while to install and cache the libraries during a user's first visit).

## Project Structure

```
.
├── LICENSE
├── app
│   ├── app.py
│   ├── ratelimit.py
│   └── requirements.txt
├── data
│   ├── EGAD PFAS Statewide File November 2023 V1-1f.xlsx
│   ├── cleaned_data.csv
│   ├── geojson_maine_towns.json
│   ├── preprocess_data.ipynb
│   └── sample_key.csv
└── docs
    ├── app.json
    ├── edit
    ├── index.html
    ├── shinylive
    └── shinylive-sw.js
```

### `app/`
This directory contains the core files for the ShinyLive web application:

- `app.py`: The main application script.
- `ratelimit.py`: A module to handle rate limiting within the app.
- `requirements.txt`: Lists the Python dependencies required to run the app.

### `data/`
This directory contains the data files used in the application:

- `EGAD PFAS Statewide File November 2023 V1-1f.xlsx`: The raw statewide PFAS data. Downloaded from https://www.maine.gov/dep/spills/topics/pfas/#Data.
- `cleaned_data.csv`: The processed version of the data for use in the app.
- `geojson_maine_towns.json`: A GeoJSON file representing the geographical boundaries of towns in Maine. Downloaded from https://maine.hub.arcgis.com/datasets/b0c7b943162f45e48b3a829b7f35709a/explore?location=45.115741%2C-68.974254%2C6.97, with edits made to match town names in raw .xlsx data.
- `preprocess_data.ipynb`: A Jupyter notebook containing the code used to clean and preprocess the raw data.
- `sample_key.csv`: A key file used for understanding or merging data.

### `docs/`
This directory contains static files for deploying the app using GitHub Pages:

- `index.html`: The entry point for the web app.
- `shinylive/` & `shinylive-sw.js`: Supporting files for the ShinyLive app.
- `app.json`: Configuration file for the app deployment.
- `edit/`: Contains editable resources or configurations for the documentation.

### `LICENSE`
The license file for the project.

## Installation

To run this web application locally, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/matthewse19/maine_pfas.git
   cd maine_pfas
   ```

2. **Install ShinyLive with pip:**
   ```bash
   pip install shinylive
   ```

3. **Build and run the app:**
   ```bash
   shinylive export app docs/
   python3 -m http.server --directory docs --bind localhost 8080
   ```

4. **Open your browser and go to:**
   ```
   http://localhost:8080
   ```

## License

This project is licensed under the terms of the `LICENSE` file in this repository.
