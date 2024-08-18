from shiny import App, ui, render, reactive
import geopandas as gpd
import pandas as pd
from pyodide.http import open_url
import folium
from io import StringIO
from ratelimit import debounce, throttle

na_color = "#ccccccff"
legend_colors = ["#5bb6a9ff", "#ceeb9cff", "#fdcc7aff", "#ed6345ff", "#9e0142ff"]
legend_splits = [0, 50, 100, 500, 1000]
legend_labels = [
    f"[{legend_splits[i]} - {legend_splits[i+1]}%)"
    for i in range(len(legend_splits) - 1)
]
legend_labels.append(f"[{legend_splits[-1]}% +")


def color_lookup(x):
    if pd.isna(x):
        return na_color
    for color, upper_bound in zip(legend_colors[:-1], legend_splits[1:]):
        if x < upper_bound:
            return color

    return legend_colors[-1]


# Define thresholds
thresholds = {
    "Drinking Water": {
        "PFOA": 4,
        "PFOS": 4,
        "PFHXS": 10,
        "HFPO-DA": 10,
        "PFNA": 10,
        "SUM OF 6 PFAS": 20,
    },
    "Soil": {
        "PFOA": 740,
        "PFOS": 490,
        "PFHXS": 4900,
        "PFNA": 740,
        "PFBS": 74000,
        "PFBA": 300000,
        "PFHXA": 120000,
    },
    "Milk": {"PFOS": 210},
    "Meat": {"PFOS": 3.4},
    "Filet": {"PFOS": 3.5},
}

units = {
    "Drinking Water": "ng/L",
    "Soil": "ng/g",
    "Milk": "ng/L",
    "Meat": "ng/g",
    "Filet": "ng/g",
}

sample_types = list(thresholds.keys())

defaultChem = "PFOA"

cleaned_data_file = open_url(
    "https://raw.githubusercontent.com/matthewse19/maine_pfas/main/data/cleaned_data.csv"
)

df = pd.read_csv(cleaned_data_file)
df["sample_date"] = pd.to_datetime(df["sample_date"])
min_date = min(df["sample_date"])
max_date = max(df["sample_date"])
df["threshold_pct"] = df["threshold_pct"].astype(float)


# round values > 1 to 2 decimal places, keep 3 significant decimal places for values < 1
def custom_round(number):
    if pd.isna(number):
        return number
    if number > 1:
        return round(number, 2)
    elif 0 < number < 1:
        return round(number, -int(format(number, ".1e").split("e")[1]) + 2)
    else:
        return number  # for handling 1, 0, or negative numbers if necessary


df["threshold_pct"] = df["threshold_pct"].apply(custom_round)


# Load the GeoJSON data
geo_json_file = open_url(
    "https://raw.githubusercontent.com/matthewse19/maine_pfas/main/data/geojson_maine_towns.json"
)
geojson_data = gpd.read_file(geo_json_file)
geojson_data = geojson_data.drop(["created_date", "last_edited_date"], axis=1)
geojson_data = geojson_data.rename({"TOWN": "town"}, axis=1)


# Filter dataframe to get the maximum concentration for each town
disp_data = (
    df[df["parameter"] == defaultChem]
    .groupby("town")["concentration"]
    .max()
    .reset_index()
)

# Merge GeoJSON data with the filtered concentration data
geo_disp_data = geojson_data.merge(disp_data, how="inner", on="town")

get_checkbox_name = lambda x: f"{x.replace(' ', '_')}_checkbox"

sample_threshold_checkboxes = [
    ui.input_checkbox_group(
        get_checkbox_name(sample_type),
        label=f"{sample_type}",
        choices={
            parameter: f"{parameter} - {threshold:,} {units[sample_type]}"
            for parameter, threshold in thresholds[sample_type].items()
        },
        selected=(
            list(thresholds[sample_type].keys())
            if sample_type == "Drinking Water"
            else []
        ),
    )
    for sample_type in sample_types
]

# Define UI for application
app_ui = ui.page_fluid(
    ui.panel_title("PFAS Readings in Maine Towns"),
    ui.panel_well(
        ui.p(
            """This page displays the most recent readings of PFAS chemicals gathered by the Maine Department of Environmental Protection (DEP), and displays these measurements
        as a percentage of their Maximum Containment Level (MCL) or their Remedial Action Guideline (RAG) Screen Levels, as defined by the 
        EPA and Maine DEP respectively.
        """
        ),
        ui.p(
            ui.strong("Reading the map: "),
            "The color of each town corresponds with the reading which was the  ",
            ui.em("highest percentage"),
            " of the chemical and sample type's threshold (either MCL or RAG).",
        ),
        ui.p(
            """The data can be aggregated and filtered by type of chemical, sample type, or date of measurement with the panel on the left.
            """
        ),
        ui.p(
            """See below for further information on sources, methodology, and more links.
            """
        ),
    ),
    ui.layout_sidebar(
        ui.sidebar(
            (
                ui.output_ui("legend"),
                *sample_threshold_checkboxes,
                ui.input_date_range(
                    "date_range",
                    label="Test date range",
                    start=min_date,
                    end=max_date,
                    min=min_date,
                    max=max_date + pd.DateOffset(1),
                    startview="year",
                ),
            ),
            width="20%",
        ),
        ui.output_ui("map", fill=True, fillable=True),
    ),
    ui.card(
        ui.card_header("Further info & sources"),
        ui.strong("Thresholds - MCLs and RAGs"),
        ui.p(
            "The MCLs for drinking water created by the EPA for PFOA, PFOS, PFHxS, PFNA, and HFPO-DA can be found at ",
            ui.a(
                "[1]",
                href=r"https://www.epa.gov/sdwa/and-polyfluoroalkyl-substances-pfas",
            ),
            '. Additionally, Maine DEP has an residential drinking water standard for "SUM OF 6 PFAS", which is the sum of PFOS + PFOA + PFHpA + PFNA + PFHxS + PFDA ',
            ui.a(
                "[2]",
                href=r"https://www.maine.gov/dep/spills/topics/pfas/Maine%20PFAS%20Screening%20Levels_Rev_12_4_23.pdf",
            ),
            ".",
        ),
        ui.p(
            """The Maine DEP also has RAGs for milk, meat, and fissue tissue (filet). There are also different guidelines for soil depending on
            where the soil is found. For simplicity, the above soil thresholds are from the "Park User" category,
             regardless of where the soil sample was taken (and the units are in ng/g)
            """,
            ui.a(
                "[2]",
                href=r"https://www.maine.gov/dep/spills/topics/pfas/Maine%20PFAS%20Screening%20Levels_Rev_12_4_23.pdf",
            ),
            ".",
        ),
        ui.strong("Data"),
        ui.p(
            "The raw data can be accessed at ",
            ui.a("[3]", href="https://www.maine.gov/dep/spills/topics/pfas/#Data"),
            " and the processed data can be found in the below GitHub repository.",
        ),
        ui.strong("Sources"),
        ui.p(
            r"[1] Environmental Protection Agency. (n.d.). Per- and Polyfluoroalkyl Substances (PFAS). EPA.\n\thttps://www.epa.gov/sdwa/and-polyfluoroalkyl-substances-pfas"
        ),
        ui.p(
            r"[2] MAINE PFAS SCREENING LEVELS . maine.gove. (2023, December). https://www.maine.gov/dep/spills/topics/pfas/Maine%20PFAS%20Screening%20Levels_Rev_12_4_23.pdf"
        ),
        ui.p(
            r"[3] Per- and polyfluoroalkyl substances (PFAS). Maine Department of Environmental Protection. (n.d.). https://www.maine.gov/dep/spills/topics/pfas/#Data"
        ),
        ui.card_footer("See ", ui.a("https://github.com/matthewse19/maine_pfas")),
    ),
)


# Define server logic
def server(input, output, session):
    @debounce(0.75)
    @reactive.Calc
    def debounced_sample_check_values():
        sample_check_values = {
            sample_type: input[get_checkbox_name(sample_type)]()
            for sample_type in sample_types
        }

        return sample_check_values

    @reactive.Calc
    def data_filtered():
        # Get the selected date range
        start_date = input.date_range()[0]
        end_date = input.date_range()[1]

        disp_data_filtered = df[
            (df["sample_date"] >= pd.to_datetime(start_date))
            & (df["sample_date"] <= pd.to_datetime(end_date))
        ]

        # filter data according to checkboxes
        def chems_sample_filter(chems, sample):
            return (
                lambda row: row["parameter"] in chems and row["sample_type"] == sample
            )

        sample_check_values = debounced_sample_check_values()
        all_filters = [
            chems_sample_filter(sample_check_values[sample_type], sample_type)
            for sample_type in thresholds.keys()
        ]
        row_all_filters = lambda row: any(f(row) for f in all_filters)
        disp_data_filtered = disp_data_filtered[
            disp_data_filtered.apply(row_all_filters, axis=1)
        ]

        # get idxs of max values in each grouped town
        max_ids = (
            disp_data_filtered.groupby("town")["threshold_pct"].transform("max")
            == disp_data_filtered["threshold_pct"]
        )
        # get entire DF, and only keep one row per town (arbitrarily keep first)
        disp_data_filtered = disp_data_filtered[max_ids].drop_duplicates(["town"])
        disp_data_filtered["sample_date"] = disp_data_filtered["sample_date"].astype(
            str
        )

        if len(disp_data_filtered) == 0:
            return None

        return geojson_data.merge(disp_data_filtered, how="inner", on="town")

    @output
    @render.ui
    def legend():
        # Create HTML for the legend
        legend_html = (
            '<div style="padding: 10px; border: 2px solid black; width: 150px;">'
        )
        legend_html += "<b>% of chemical threshold</b><br>"
        for color, label in zip(legend_colors, legend_labels):
            legend_html += f'<div style="display: flex; align-items: center;"><div style="width: 20px; height: 20px; background-color: {color}; margin-right: 5px;"></div>{label}</div>'
        legend_html += "</div>"

        return ui.HTML(legend_html)

    @output
    @render.ui
    def map():
        geojson = data_filtered()
        if geojson is None:
            return None

        m = folium.Map(
            location=[45.2538, -69.4455],
            zoom_start=7,
            tiles="CartoDB Positron",
        )
        geo = folium.GeoJson(
            data=geojson,
            style_function=lambda feature: {
                "fillColor": color_lookup(feature["properties"]["threshold_pct"]),
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.7,
            },
        ).add_to(m)

        folium.GeoJsonTooltip(
            [
                "town",
                "threshold_pct",
                "parameter",
                "concentration",
                "units",
                "sample_type",
                "current_site_name",
                "sample_date",
                "ts",
            ],
            aliases=[
                "Town",
                "% of threshold",
                "Chemical",
                "Concentration",
                "Units",
                "Sample type",
                "Site name",
                "Date",
                "Treatment status",
            ],
            style="font-size: medium",
            localize=True,
        ).add_to(geo)

        return m


# Run the application
app = App(app_ui, server)

if __name__ == "__main__":
    app.run()
