import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
CLEAN_DATA_DIR = Path("cleaned_data")
PLOTS_DIR = Path("plots")
PLOTS_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid")

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def _load_clean(filename: str) -> pd.DataFrame:
    path = CLEAN_DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run data_cleaning.py first.")
    return pd.read_csv(path, parse_dates=[col for col in ["ship_date", "delivery_date", "date"] if col in pd.read_csv(path, nrows=0).columns])


def plot_delivery_times_by_route(shipments_df: pd.DataFrame, top_n: int = 15):
    """Creates a boxplot of delivery (transit) times for the top N busiest routes."""
    # Compute transit time in hours
    shipments_df = shipments_df.dropna(subset=["ship_date", "delivery_date"]).copy()
    shipments_df["transit_hours"] = (
        shipments_df["delivery_date"] - shipments_df["ship_date"]
    ).dt.total_seconds() / 3600

    # Select top N routes by shipment count
    top_routes = (
        shipments_df["route_id"].value_counts().head(top_n).index.tolist()
    )
    subset = shipments_df[shipments_df["route_id"].isin(top_routes)]

    plt.figure(figsize=(12, 6))
    sns.boxplot(
        data=subset,
        x="route_id",
        y="transit_hours",
        color="skyblue",
    )
    plt.title(f"Transit time distribution for top {top_n} routes")
    plt.ylabel("Transit time (hours)")
    plt.xlabel("Route ID")
    plt.xticks(rotation=45)
    plt.tight_layout()

    outfile = PLOTS_DIR / "delivery_time_by_route.png"
    plt.savefig(outfile, dpi=120)
    plt.close()
    print(f"📊 Saved delivery time plot → {outfile}")


def plot_weekly_delay_patterns(delays_df: pd.DataFrame):
    """Creates a heatmap showing average delay hours by day of week and hour of day."""
    if "date" not in delays_df.columns:
        raise ValueError("'date' column missing in delays dataset")

    delays_df["date"] = pd.to_datetime(delays_df["date"], errors="coerce")
    delays_df["day_of_week"] = delays_df["date"].dt.day_name()
    delays_df["hour_of_day"] = delays_df["date"].dt.hour

    # Categorize days to maintain order
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    delays_df["day_of_week"] = pd.Categorical(
        delays_df["day_of_week"], categories=day_order, ordered=True
    )

    pivot = delays_df.pivot_table(
        values="delay_hours",
        index="day_of_week",
        columns="hour_of_day",
        aggfunc="mean",
    )

    plt.figure(figsize=(14, 6))
    sns.heatmap(
        pivot,
        cmap="Reds",
        linewidths=0.3,
        linecolor="white",
        cbar_kws={"label": "Average delay (hours)"},
    )
    plt.title("Average delay hours by day of week and hour of day")
    plt.xlabel("Hour of day")
    plt.ylabel("")
    plt.tight_layout()

    outfile = PLOTS_DIR / "delay_heatmap.png"
    plt.savefig(outfile, dpi=120)
    plt.close()
    print(f"📊 Saved weekly delay heatmap → {outfile}")


# -------------------------------------------------------------------
# Main routine
# -------------------------------------------------------------------

def main():
    print("\n⏳ Loading cleaned datasets...")
    shipments_df = _load_clean("shipments_clean.csv")
    delays_df = _load_clean("delays_clean.csv")

    print("✨ Generating visualizations...")
    plot_delivery_times_by_route(shipments_df)
    plot_weekly_delay_patterns(delays_df)

    print(f"✔️ All plots saved in '{PLOTS_DIR.resolve()}'")


if __name__ == "__main__":
    main()