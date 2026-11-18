import os
import shutil
import tempfile
import pandas as pd
import numpy as np
import pytest
from datetime import datetime

from backend.app.ml.schemas.config import PipelineConfig
from backend.app.ml.preprocessing.timestamp import TimestampProcessor
from backend.app.ml.preprocessing.outliers import OutlierHandler
from backend.app.ml.data.validator import DataValidator
from backend.app.ml.features.spatial import SpatialFeatures
from backend.app.ml.features.temporal import TemporalFeatures
from backend.app.ml.features.demand import DemandPressureFeatures
from backend.app.ml.features.engineer import FeatureEngineer
from backend.app.ml.datasets.builder import TargetBuilder, DatasetBuilder
from backend.app.ml.data.splitter import ChronologicalSplitter
from backend.app.ml.data.exporter import DatasetExporter
from backend.app.ml.pipeline import PreprocessingPipeline


@pytest.fixture
def sample_orders_df():
    """Generates a small representative DataFrame reflecting real Kaggle fields."""
    return pd.DataFrame({
        "order_id": [1001, 1002, 1003, 1004, 1005, 1005],  # 1005 is duplicate
        "order_time": [
            "2021-01-26 23:50:00",  # Crosses midnight
            "2021-01-27 12:10:00",
            "2021-02-03 14:00:00",  # Val partition
            "2021-02-05 18:30:00",  # Test partition
            "2021-02-05 19:00:00",  # Test partition
            "2021-02-05 19:00:00",  # Duplicate row
        ],
        "order_date": [
            "2021-01-26 00:00:00",
            "2021-01-27 00:00:00",
            "2021-02-03 00:00:00",
            "2021-02-05 00:00:00",
            "2021-02-05 00:00:00",
            "2021-02-05 00:00:00",
        ],
        "allot_time": [
            "2021-01-26 23:51:00",
            "2021-01-27 12:15:00",  # 5 min delay (>3 min)
            "2021-02-03 14:00:30",
            "2021-02-05 18:30:15",
            "2021-02-05 19:01:00",
            "2021-02-05 19:01:00",
        ],
        "accept_time": [
            "2021-01-26 23:51:30",
            "2021-01-27 12:14:00",  # Negative accept delay (accept < allot)
            "2021-02-03 14:01:00",
            "2021-02-05 18:31:00",
            "2021-02-05 19:02:00",
            "2021-02-05 19:02:00",
        ],
        "pickup_time": [
            "2021-01-27 00:05:00",  # Past midnight
            "2021-01-27 12:30:00",
            "2021-02-03 14:15:00",
            None,                   # Cancelled before pickup
            "2021-02-05 19:15:00",
            "2021-02-05 19:15:00",
        ],
        "delivered_time": [
            "2021-01-27 00:25:00",  # Past midnight: duration = 35 min
            "2021-01-27 12:55:00",  # duration = 45 min
            "2021-02-03 14:35:00",  # duration = 35 min
            None,
            "2021-02-05 19:02:00",  # duration = 2 min (< 5 min outlier)
            "2021-02-05 19:02:00",
        ],
        "cancelled_time": [
            None,
            None,
            None,
            "2021-02-05 18:35:00",  # Cancelled at allot + 4.75m
            None,
            None,
        ],
        "cancelled": [0, 0, 0, 1, 0, 0],
        "rider_id": [101, 102, 103, 104, 105, 105],
        "first_mile_distance": [1.2, 2.5, 0.8, 1.5, 25.0, 25.0],  # 25.0 > 20 km outlier
        "last_mile_distance": [3.5, 0.0, 4.2, 2.1, 5.0, 5.0],     # 0.0 is zero distance
        "session_time": [60.0, 120.0, 180.0, 45.0, 500.0, 500.0], # 500.0 > 480 min fatigue
    })


def test_timestamp_processor_midnight_and_intervals(sample_orders_df):
    """Verifies that timestamp parsing correctly computes milestone delays across midnight."""
    processor = TimestampProcessor()
    df_ts = processor.process(sample_orders_df)

    # 1. Check order 1001 (placed 23:50 on Jan 26, delivered 00:25 on Jan 27)
    row_1001 = df_ts[df_ts["order_id"] == 1001].iloc[0]
    assert row_1001["allot_delay_min"] == pytest.approx(1.0)
    assert row_1001["accept_delay_min"] == pytest.approx(0.5)
    assert row_1001["pickup_delay_min"] == pytest.approx(13.5)
    assert row_1001["transit_duration_min"] == pytest.approx(20.0)
    assert row_1001["delivery_duration_min"] == pytest.approx(35.0)

    # 2. Check negative acceptance delay for order 1002 (accept at 12:14, allot at 12:15)
    row_1002 = df_ts[df_ts["order_id"] == 1002].iloc[0]
    assert row_1002["accept_delay_min"] == pytest.approx(-1.0)


def test_data_validator_duplicate_and_anomalies(sample_orders_df):
    """Verifies that DataValidator detects duplicates and operational anomalies."""
    processor = TimestampProcessor()
    df_ts = processor.process(sample_orders_df)

    validator = DataValidator()
    df_clean, report = validator.validate_and_deduplicate(df_ts)

    # Duplicate detection
    assert report.duplicate_rows_dropped == 1
    assert report.duplicate_order_ids == [1005]
    assert len(df_clean) == 5

    # Anomalies
    assert report.negative_accept_delay_count == 1
    assert report.zero_last_mile_count == 1
    assert report.extreme_first_mile_count == 1
    assert report.duration_under_5min_count == 1
    assert report.cancelled_count == 1
    assert report.cancelled_pre_pickup_count == 1


def test_training_only_imputation_isolation():
    """
    Directly verifies Objective 1 & 5:
    Fitted imputation statistics on training partition are completely unaffected by
    extreme or corrupted values in validation or test data.
    """
    train_data = pd.DataFrame({
        "last_mile_distance": [2.0, 3.0, 4.0],  # median = 3.0
        "session_time": [100.0, 200.0, 300.0],  # median = 200.0
    })
    val_data = pd.DataFrame({
        "last_mile_distance": [0.0, 99999.0],   # extreme values
        "session_time": [None, 99999.0],
    })

    # Fit exclusively on train_data
    outlier_handler = OutlierHandler().fit(train_data)
    feature_engineer = FeatureEngineer().fit(train_data)

    assert outlier_handler.fitted_median_last_mile == pytest.approx(3.0)
    assert feature_engineer.fitted_median_session_time == pytest.approx(200.0)

    # Transform val_data using fitted parameters
    val_imputed = outlier_handler.handle_distances(val_data)
    # The zero value in val_data must be imputed with train median (3.0), NOT val median
    assert val_imputed.loc[0, "last_mile_distance"] == pytest.approx(3.0)
    assert val_imputed.loc[0, "is_zero_last_mile"] == 1


def test_outlier_handler_distances_and_duration_filtering(sample_orders_df):
    """Verifies that invalid distances are imputed with indicators and duration outliers filtered."""
    processor = TimestampProcessor()
    df_ts = processor.process(sample_orders_df)
    validator = DataValidator()
    df_clean, _ = validator.validate_and_deduplicate(df_ts)

    handler = OutlierHandler(min_duration_min=5.0, max_duration_min=180.0)
    handler.fit(df_clean)  # fit on sample clean
    df_imputed = handler.handle_distances(df_clean)

    # Check zero distance handling
    row_1002 = df_imputed[df_imputed["order_id"] == 1002].iloc[0]
    assert row_1002["is_zero_last_mile"] == 1
    assert row_1002["last_mile_distance"] == pytest.approx(handler.fitted_median_last_mile)

    # Check extreme first mile capping
    row_1005 = df_imputed[df_imputed["order_id"] == 1005].iloc[0]
    assert row_1005["is_extreme_first_mile"] == 1
    assert row_1005["first_mile_distance"] == pytest.approx(20.0)

    # Check duration filtering: Order 1005 duration = 2.0 min (< 5.0 min) must be excluded
    eligible_df, exclusions = handler.filter_delivery_duration_cohort(df_imputed)
    assert exclusions["under_min_duration_excluded"] == 1
    assert 1005 not in eligible_df["order_id"].values
    assert 1001 in eligible_df["order_id"].values
    assert 1002 in eligible_df["order_id"].values


def test_feature_availability_and_leakage_control():
    """Verifies that Order Creation feature lists contain strictly ZERO downstream features."""
    order_time_features = DatasetBuilder.ORDER_TIME_FEATURE_COLUMNS

    forbidden_leaks = [
        "pickup_time", "delivered_time", "allot_time", "accept_time",
        "first_mile_distance", "rider_id", "session_time", "reassigned_order",
        "reassignment_method", "reassignment_reason", "alloted_orders",
        "delivered_orders", "undelivered_orders", "lifetime_order_count",
        "cancelled_time",
    ]

    for forbidden in forbidden_leaks:
        assert forbidden not in order_time_features, f"Critical feature leak detected: {forbidden} present in order-time feature set!"


def test_rolling_demand_temporal_isolation():
    """
    Directly verifies Objective 3:
    Rolling demand features are strictly backward-looking (closed='left').
    No future or simultaneous orders contribute to the rolling count.
    """
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4],
        "order_time": pd.to_datetime([
            "2021-01-26 10:00:00",
            "2021-01-26 10:05:00",
            "2021-01-26 10:05:00",  # Same second as #2
            "2021-01-26 10:20:00",  # 20 min after #1
        ]),
    })

    res = DemandPressureFeatures.extract_rolling_demand(df)

    # Order 1 (at 10:00): zero orders in past 15m or 60m
    assert res.loc[0, "rolling_order_volume_15m"] == 0.0
    assert res.loc[0, "rolling_order_volume_60m"] == 0.0

    # Order 2 (at 10:05): exactly 1 past order (Order 1)
    assert res.loc[1, "rolling_order_volume_15m"] == 1.0

    # Order 3 (at 10:05, exact same second): still only 1 past order (Order 2 does not leak into Order 3)
    assert res.loc[2, "rolling_order_volume_15m"] == 1.0

    # Order 4 (at 10:20): Order 1 is outside 15m, but Orders 2 & 3 are inside 15m (count = 2)
    assert res.loc[3, "rolling_order_volume_15m"] == 2.0
    # In past 60m, Orders 1, 2, 3 are all inside (count = 3)
    assert res.loc[3, "rolling_order_volume_60m"] == 3.0


def test_demand_acceleration_edge_cases():
    """Verifies that demand acceleration handles zero counts and extreme surges safely without division by zero."""
    df = pd.DataFrame({
        "order_id": [1, 2],
        "order_time": pd.to_datetime(["2021-01-26 01:00:00", "2021-01-26 02:00:00"]),
    })
    res = DemandPressureFeatures.extract_rolling_demand(df)

    # When both 15m and 60m volume are 0, acceleration must be 0.0 (not NaN or Inf)
    assert res.loc[0, "demand_acceleration"] == 0.0
    assert not np.isnan(res.loc[0, "demand_acceleration"])
    assert not np.isinf(res.loc[0, "demand_acceleration"])


def test_cancellation_landmark_eligibility_and_horizon():
    """
    Directly verifies Objective 4:
    Excludes orders cancelled or delivered before t_allot + 5m.
    Assigns target 1 if order cancels post-landmark, 0 if delivered post-landmark.
    """
    df = pd.DataFrame({
        "order_id": [101, 102, 103, 104],
        "allot_time": pd.to_datetime([
            "2021-01-26 12:00:00",
            "2021-01-26 12:00:00",
            "2021-01-26 12:00:00",
            "2021-01-26 12:00:00",
        ]),
        "cancelled": [1, 0, 1, 0],
        # Landmark is 12:05:00
        "cancelled_time": pd.to_datetime([
            "2021-01-26 12:03:00",  # Cancelled BEFORE landmark (must be EXCLUDED)
            None,
            "2021-01-26 12:25:00",  # Cancelled AFTER landmark (must be INCLUDED, target=1)
            None,
        ]),
        "delivered_time": pd.to_datetime([
            None,
            "2021-01-26 12:04:00",  # Delivered BEFORE landmark (must be EXCLUDED)
            None,
            "2021-01-26 12:35:00",  # Delivered AFTER landmark (must be INCLUDED, target=0)
        ]),
    })

    cohort_df, exclusions = TargetBuilder.build_landmark_cancellation_target(df, landmark_offset_min=5.0)

    # Order 101 (cancelled at 12:03) and Order 102 (delivered at 12:04) must be excluded
    assert exclusions["cancelled_prior_to_landmark"] == 1
    assert exclusions["delivered_prior_to_landmark"] == 1
    assert exclusions["active_at_landmark_rows"] == 2

    assert 101 not in cohort_df["order_id"].values
    assert 102 not in cohort_df["order_id"].values
    assert 103 in cohort_df["order_id"].values
    assert 104 in cohort_df["order_id"].values

    # Check target
    row_103 = cohort_df[cohort_df["order_id"] == 103].iloc[0]
    row_104 = cohort_df[cohort_df["order_id"] == 104].iloc[0]
    assert row_103["target_cancelled_post_landmark"] == 1
    assert row_104["target_cancelled_post_landmark"] == 0


def test_chronological_splitter_partitions():
    """Verifies that chronological splitting enforces Phase 2.1 partitions without overlap."""
    dates = pd.date_range("2021-01-26 06:00:00", "2021-02-06 06:00:00", freq="12h")
    df = pd.DataFrame({
        "order_id": list(range(len(dates))),
        "order_time": dates,
        "feature_1": np.random.randn(len(dates)),
    })

    splitter = ChronologicalSplitter()
    train_df, val_df, test_df, stats = splitter.split(df)

    assert len(train_df) + len(val_df) + len(test_df) == len(df)
    assert train_df["order_time"].max() < pd.Timestamp("2021-02-03 00:00:00")
    assert val_df["order_time"].min() >= pd.Timestamp("2021-02-03 00:00:00")
    assert val_df["order_time"].max() < pd.Timestamp("2021-02-05 00:00:00")
    assert test_df["order_time"].min() >= pd.Timestamp("2021-02-05 00:00:00")

    # Order ID uniqueness across splits
    train_set = set(train_df["order_id"])
    val_set = set(val_df["order_id"])
    test_set = set(test_df["order_id"])
    assert len(train_set.intersection(val_set)) == 0
    assert len(val_set.intersection(test_set)) == 0
    assert len(train_set.intersection(test_set)) == 0


def test_dataset_export_and_parquet_reimport(sample_orders_df):
    """Verifies that Parquet datasets and JSON metadata can be exported and re-imported cleanly."""
    temp_dir = tempfile.mkdtemp()
    try:
        processor = TimestampProcessor()
        df_ts = processor.process(sample_orders_df)
        validator = DataValidator()
        df_clean, _ = validator.validate_and_deduplicate(df_ts)
        handler = OutlierHandler().fit(df_clean)
        df_imputed = handler.handle_distances(df_clean)
        engineer = FeatureEngineer().fit(df_clean)
        df_feats = engineer.generate_order_time_features(df_imputed)

        target_builder = TargetBuilder()
        df_with_target = target_builder.build_allocation_delay_target(df_feats)

        dataset_builder = DatasetBuilder()
        matrix = dataset_builder.build_allocation_delay_matrix(df_with_target)

        splitter = ChronologicalSplitter()
        train_df, val_df, test_df, _ = splitter.split(matrix)

        exporter = DatasetExporter(base_output_dir=temp_dir)
        from backend.app.ml.schemas.metadata import DatasetMetadata, TargetMetadata

        meta = DatasetMetadata(
            task_name="test_alloc",
            prediction_point="t_order",
            eligible_cohort_description="Test cohort",
            total_rows=len(matrix),
            train_rows=len(train_df),
            val_rows=len(val_df),
            test_rows=len(test_df),
            features=[f.__dict__ for f in dataset_builder.get_order_time_feature_metadata()],
            target=TargetMetadata("test_target", "BINARY_CLASSIFICATION", "Test").__dict__,
            exclusions_log={},
            leakage_exclusions=[],
            fitted_parameters={"fitted_median": 2.67},
        )

        export_info = exporter.export_task_dataset("test_alloc", train_df, val_df, test_df, meta)

        assert os.path.exists(export_info["train_path"])
        assert os.path.exists(export_info["val_path"])
        assert os.path.exists(export_info["test_path"])
        assert os.path.exists(export_info["metadata_path"])

        # Re-import test
        df_reimported = pd.read_parquet(export_info["train_path"])
        assert len(df_reimported) == len(train_df)
        assert list(df_reimported.columns) == list(train_df.columns)

    finally:
        shutil.rmtree(temp_dir)


def test_pipeline_reproducibility(sample_orders_df):
    """Verifies that running feature transformations twice yields byte-for-byte identical results."""
    processor = TimestampProcessor()
    df1 = processor.process(sample_orders_df)
    df2 = processor.process(sample_orders_df)
    pd.testing.assert_frame_equal(df1, df2)

    engineer = FeatureEngineer().fit(df1)
    f1 = engineer.generate_order_time_features(df1)
    f2 = engineer.generate_order_time_features(df2)
    pd.testing.assert_frame_equal(f1, f2)
