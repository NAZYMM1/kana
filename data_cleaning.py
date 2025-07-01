import pandas as pd
from pathlib import Path

# Define input and output directories
RAW_DATA_DIR = Path("data")  # place raw CSV files here
CLEAN_DATA_DIR = Path("cleaned_data")
CLEAN_DATA_DIR.mkdir(exist_ok=True)


def _load_csv(filename: str) -> pd.DataFrame:
    """Read a CSV file from RAW_DATA_DIR into a DataFrame."""
    path = RAW_DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Please ensure the raw data file exists.")
    return pd.read_csv(path)


# -------------------------
# Cleaning helpers
# -------------------------

def _standardize_strings(series: pd.Series) -> pd.Series:
    """Lower-case and strip whitespace from a pandas Series of strings."""
    return series.astype(str).str.lower().str.strip()


def _fill_numeric_by_group_median(df: pd.DataFrame, group_col: str, numeric_cols: list[str]):
    """Fill NA in *numeric_cols* with the median calculated within *group_col* groups."""
    for col in numeric_cols:
        df[col] = df.groupby(group_col)[col].transform(lambda s: s.fillna(s.median()))


# -------------------------
# Dataset-specific cleaners
# -------------------------

def clean_shipments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Rename Russian column names to snake_case English if needed
    rename_map = {
        "дата отправки": "ship_date",
        "дата доставки": "delivery_date",
        "вес": "weight",
        "стоимость": "cost",
        "отправитель": "sender",
        "получатель": "recipient",
        "маршрут": "route_id",
        "статус": "status",
    }
    df.rename(columns=rename_map, inplace=True)

    # Datetime conversion
    df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")
    df["delivery_date"] = pd.to_datetime(df["delivery_date"], errors="coerce")

    # Numeric conversion & imputation
    for col in ["weight", "cost"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    _fill_numeric_by_group_median(df, "route_id", ["weight", "cost"])

    # Text normalization
    for col in ["sender", "recipient", "status"]:
        df[col] = _standardize_strings(df[col])

    # Duplicates removal
    df = df.drop_duplicates()
    return df


def clean_routes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {
        "маршрут_id": "route_id",
        "начальный пункт": "origin",
        "конечный пункт": "destination",
        "расстояние": "distance",
        "среднее время в пути": "avg_time",
        "средняя стоимость": "avg_cost",
    }
    df.rename(columns=rename_map, inplace=True)

    # Numeric columns
    for col in ["distance", "avg_time", "avg_cost"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Text normalization
    df["origin"] = _standardize_strings(df["origin"])
    df["destination"] = _standardize_strings(df["destination"])

    df = df.drop_duplicates()
    return df


def clean_warehouses(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {
        "регион": "region",
        "емкость": "capacity",
        "текущее заполнение": "current_fill",
    }
    df.rename(columns=rename_map, inplace=True)

    df["region"] = _standardize_strings(df["region"])

    for col in ["capacity", "current_fill"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill "current_fill" NaN with overall median
    df["current_fill"].fillna(df["current_fill"].median(), inplace=True)

    df = df.drop_duplicates()
    return df


def clean_carriers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {
        "название": "name",
        "средняя оценка": "rating",
        "кол-во машин": "fleet_size",
        "надежность": "reliability",
    }
    df.rename(columns=rename_map, inplace=True)

    df["name"] = _standardize_strings(df["name"])

    for col in ["rating", "fleet_size", "reliability"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop_duplicates()
    return df


def clean_delays(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {
        "маршрут_id": "route_id",
        "дата": "date",
        "причина": "reason",
        "задержка_в_часах": "delay_hours",
    }
    df.rename(columns=rename_map, inplace=True)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["delay_hours"] = pd.to_numeric(df["delay_hours"], errors="coerce").fillna(0)

    df["reason"] = _standardize_strings(df["reason"])

    df = df.drop_duplicates()
    return df


# -------------------------
# Main routine
# -------------------------

def main() -> None:
    """Load, clean, and persist all datasets."""
    print("\n⏳ Loading raw datasets...")
    shipments_df = clean_shipments(_load_csv("shipments.csv"))
    routes_df = clean_routes(_load_csv("routes.csv"))
    warehouses_df = clean_warehouses(_load_csv("warehouses.csv"))
    carriers_df = clean_carriers(_load_csv("carriers.csv"))
    delays_df = clean_delays(_load_csv("delays.csv"))

    print("✅ Data loaded & cleaned. Saving results...")
    shipments_df.to_csv(CLEAN_DATA_DIR / "shipments_clean.csv", index=False)
    routes_df.to_csv(CLEAN_DATA_DIR / "routes_clean.csv", index=False)
    warehouses_df.to_csv(CLEAN_DATA_DIR / "warehouses_clean.csv", index=False)
    carriers_df.to_csv(CLEAN_DATA_DIR / "carriers_clean.csv", index=False)
    delays_df.to_csv(CLEAN_DATA_DIR / "delays_clean.csv", index=False)

    print(f"✨ All cleaned files saved to '{CLEAN_DATA_DIR.resolve()}'")


if __name__ == "__main__":
    main()