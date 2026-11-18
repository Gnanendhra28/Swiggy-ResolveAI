import os
import time
from typing import Dict, Any

from backend.app.ml.schemas.config import PipelineConfig
from backend.app.ml.schemas.metadata import DatasetMetadata, TargetMetadata
from backend.app.ml.data.loader import RawDataLoader
from backend.app.ml.data.validator import DataValidator
from backend.app.ml.preprocessing.timestamp import TimestampProcessor
from backend.app.ml.preprocessing.outliers import OutlierHandler
from backend.app.ml.features.engineer import FeatureEngineer
from backend.app.ml.datasets.builder import TargetBuilder, DatasetBuilder
from backend.app.ml.data.splitter import ChronologicalSplitter
from backend.app.ml.data.exporter import DatasetExporter


class PreprocessingPipeline:
    """
    End-to-end production preprocessing and feature-engineering pipeline.
    Guarantees that all learned preprocessing statistics are fitted strictly on the
    training partition, preventing validation and test data leakage.
    """

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.loader = RawDataLoader(self.config)
        self.validator = DataValidator()
        self.timestamp_processor = TimestampProcessor()
        self.outlier_handler = OutlierHandler(
            min_duration_min=self.config.min_delivery_duration_min,
            max_duration_min=self.config.max_delivery_duration_min,
            max_first_mile=self.config.first_mile_outlier_km,
        )
        self.feature_engineer = FeatureEngineer()
        self.target_builder = TargetBuilder()
        self.dataset_builder = DatasetBuilder()
        self.splitter = ChronologicalSplitter(self.config)
        self.exporter = DatasetExporter(self.config.output_base_dir)

    def run(self) -> Dict[str, Any]:
        start_time = time.time()
        print("=" * 70)
        print("STARTING SWIGGY RESOLVEAI PHASE 2.2 PREPROCESSING PIPELINE")
        print("=" * 70)

        # 1. Load Raw Data
        print(f"Loading raw dataset from {self.config.raw_orders_path}...")
        df_raw = self.loader.load_raw_orders()
        initial_raw_rows = len(df_raw)
        print(f"Loaded {initial_raw_rows:,} raw order records.")

        # 2. Timestamp Processing
        print("Standardizing timestamps to UTC datetime64 and computing milestone intervals...")
        df_ts = self.timestamp_processor.process(df_raw)

        # 3. Validation & De-duplication
        print("Validating schema and identifying anomalies...")
        df_clean, val_report = self.validator.validate_and_deduplicate(df_ts)
        print(f"Validation complete: Dropped {val_report.duplicate_rows_dropped} exact duplicate row(s).")
        print(f"Clean orders pool: {len(df_clean):,} records.")

        # 4. Training-Only Parameter Fitting (Phase 2.2.1 Leakage Audit Directives)
        # Identify the training partition strictly by timestamp
        train_mask = (df_clean["order_time"] >= self.config.train_start_date) & (
            df_clean["order_time"] < self.config.train_end_date
        )
        train_slice = df_clean[train_mask].copy()

        print(f"Fitting imputation and feature statistics strictly on TRAINING partition ({len(train_slice):,} rows)...")
        self.outlier_handler.fit(train_slice)
        self.feature_engineer.fit(train_slice)

        fitted_params = {
            "fit_partition": f"TRAIN ({self.config.train_start_date} to {self.config.train_end_date})",
            "fit_sample_size": len(train_slice),
            "fitted_median_last_mile_km": self.outlier_handler.fitted_median_last_mile,
            "fitted_median_session_time_min": self.feature_engineer.fitted_median_session_time,
        }
        print(f"  Fitted training last_mile_distance median: {self.outlier_handler.fitted_median_last_mile} km")
        print(f"  Fitted training courier session_time median: {self.feature_engineer.fitted_median_session_time} mins")

        # 5. Outlier Handling (Impute invalid distances using training-fitted values)
        print("Handling invalid distances and adding anomaly flags...")
        df_imputed = self.outlier_handler.handle_distances(df_clean)

        # 6. Feature Engineering
        print("Engineering order-creation features (spatial, temporal cyclic, rolling demand)...")
        df_with_order_features = self.feature_engineer.generate_order_time_features(df_imputed)

        print("Engineering operational landmark features (dispatch latency, courier shift, acceptance status)...")
        df_with_all_features = self.feature_engineer.generate_landmark_features(
            df_with_order_features, landmark_offset_min=self.config.landmark_offset_min
        )

        pipeline_results = {
            "validation_report": val_report.to_dict(),
            "fitted_parameters": fitted_params,
            "tasks": {},
        }

        # -------------------------------------------------------------
        # TASK A: Delivery Duration Regression
        # -------------------------------------------------------------
        print("\n" + "-" * 50)
        print("PROCESSING TASK A: Delivery Duration Regression (ETA)")
        print("-" * 50)
        eligible_duration_df, duration_exclusions = self.outlier_handler.filter_delivery_duration_cohort(
            df_with_all_features
        )
        duration_df_with_target = self.target_builder.build_delivery_duration_target(eligible_duration_df)
        duration_matrix = self.dataset_builder.build_delivery_duration_matrix(duration_df_with_target)

        d_train, d_val, d_test, d_splits = self.splitter.split(duration_matrix)

        d_target_meta = TargetMetadata(
            name="target_delivery_duration_min",
            task_type="REGRESSION",
            description="Actual elapsed minutes from order creation to customer doorstep delivery",
            stats={
                "min": float(duration_matrix["target_delivery_duration_min"].min()),
                "median": float(duration_matrix["target_delivery_duration_min"].median()),
                "mean": round(float(duration_matrix["target_delivery_duration_min"].mean()), 2),
                "max": float(duration_matrix["target_delivery_duration_min"].max()),
            },
        )

        d_dataset_meta = DatasetMetadata(
            task_name="delivery_duration",
            prediction_point="t_order (Order Creation)",
            eligible_cohort_description="Completed orders (cancelled==0) with 5.0 <= duration <= 180.0 minutes",
            total_rows=len(duration_matrix),
            train_rows=len(d_train),
            val_rows=len(d_val),
            test_rows=len(d_test),
            features=[f.__dict__ for f in self.dataset_builder.get_order_time_feature_metadata()],
            target=d_target_meta.__dict__,
            exclusions_log=duration_exclusions,
            leakage_exclusions=[
                "pickup_time", "delivered_time", "allot_time", "accept_time",
                "first_mile_distance", "rider_id", "session_time", "reassigned_order",
                "alloted_orders", "delivered_orders", "undelivered_orders", "lifetime_order_count"
            ],
            fitted_parameters=fitted_params,
        )

        d_export_info = self.exporter.export_task_dataset(
            "delivery_duration", d_train, d_val, d_test, d_dataset_meta
        )
        print(f"Task A Exported: Train={len(d_train):,}, Val={len(d_val):,}, Test={len(d_test):,} -> {d_export_info['task_dir']}")
        pipeline_results["tasks"]["delivery_duration"] = {
            "metadata": d_dataset_meta.to_dict(),
            "export_info": d_export_info,
            "split_stats": d_splits,
        }

        # -------------------------------------------------------------
        # TASK B: Rider Allocation Delay Risk (Classification)
        # -------------------------------------------------------------
        print("\n" + "-" * 50)
        print("PROCESSING TASK B: Rider Allocation Delay Risk (Binary Classification)")
        print("-" * 50)
        alloc_df_with_target = self.target_builder.build_allocation_delay_target(
            df_with_all_features, threshold_min=self.config.allocation_delay_threshold_min
        )
        alloc_matrix = self.dataset_builder.build_allocation_delay_matrix(alloc_df_with_target)

        a_train, a_val, a_test, a_splits = self.splitter.split(alloc_matrix)

        delayed_count = int((alloc_matrix["target_is_allocation_delayed"] == 1).sum())
        normal_count = int((alloc_matrix["target_is_allocation_delayed"] == 0).sum())

        a_target_meta = TargetMetadata(
            name="target_is_allocation_delayed",
            task_type="BINARY_CLASSIFICATION",
            description=f"Binary indicator if recorded allocation delay exceeded {self.config.allocation_delay_threshold_min} minutes",
            stats={
                "class_0_normal_dispatch": normal_count,
                "class_1_delayed_dispatch": delayed_count,
                "positive_rate_pct": round(delayed_count / len(alloc_matrix) * 100, 4),
            },
        )

        a_dataset_meta = DatasetMetadata(
            task_name="allocation_delay",
            prediction_point="t_order (Order Creation)",
            eligible_cohort_description="All valid placed orders (449,999 non-duplicate orders)",
            total_rows=len(alloc_matrix),
            train_rows=len(a_train),
            val_rows=len(a_val),
            test_rows=len(a_test),
            features=[f.__dict__ for f in self.dataset_builder.get_order_time_feature_metadata()],
            target=a_target_meta.__dict__,
            exclusions_log={"duplicate_dropped": val_report.duplicate_rows_dropped},
            leakage_exclusions=[
                "allot_time", "first_mile_distance", "session_time", "reassignment_reason",
                "reassigned_order", "rider_id", "accept_time", "pickup_time", "delivered_time"
            ],
            fitted_parameters=fitted_params,
        )

        a_export_info = self.exporter.export_task_dataset(
            "allocation_delay", a_train, a_val, a_test, a_dataset_meta
        )
        print(f"Task B Exported: Train={len(a_train):,}, Val={len(a_val):,}, Test={len(a_test):,} -> {a_export_info['task_dir']}")
        pipeline_results["tasks"]["allocation_delay"] = {
            "metadata": a_dataset_meta.to_dict(),
            "export_info": a_export_info,
            "split_stats": a_splits,
        }

        # -------------------------------------------------------------
        # TASK C1: Cancellation Upfront Risk (at t_order)
        # -------------------------------------------------------------
        print("\n" + "-" * 50)
        print("PROCESSING TASK C1: Order Creation Cancellation Risk")
        print("-" * 50)
        cancel_df_with_target = self.target_builder.build_cancellation_target(df_with_all_features)
        cancel_matrix = self.dataset_builder.build_cancellation_order_time_matrix(cancel_df_with_target)

        c_train, c_val, c_test, c_splits = self.splitter.split(cancel_matrix)

        cancel_count = int((cancel_matrix["target_is_cancelled"] == 1).sum())
        fulfilled_count = int((cancel_matrix["target_is_cancelled"] == 0).sum())

        c_target_meta = TargetMetadata(
            name="target_is_cancelled",
            task_type="BINARY_CLASSIFICATION",
            description="Binary indicator if order is aborted or cancelled at any point in its lifecycle",
            stats={
                "class_0_fulfilled": fulfilled_count,
                "class_1_cancelled": cancel_count,
                "positive_rate_pct": round(cancel_count / len(cancel_matrix) * 100, 4),
            },
        )

        c_dataset_meta = DatasetMetadata(
            task_name="cancellation",
            prediction_point="t_order (Order Creation)",
            eligible_cohort_description="All valid placed orders (449,999 non-duplicate orders)",
            total_rows=len(cancel_matrix),
            train_rows=len(c_train),
            val_rows=len(c_val),
            test_rows=len(c_test),
            features=[f.__dict__ for f in self.dataset_builder.get_order_time_feature_metadata()],
            target=c_target_meta.__dict__,
            exclusions_log={"duplicate_dropped": val_report.duplicate_rows_dropped},
            leakage_exclusions=[
                "cancelled_time", "delivered_time", "pickup_time", "accept_time",
                "allot_time", "rider_id", "first_mile_distance", "session_time"
            ],
            fitted_parameters=fitted_params,
        )

        c_export_info = self.exporter.export_task_dataset(
            "cancellation", c_train, c_val, c_test, c_dataset_meta
        )
        print(f"Task C1 Exported: Train={len(c_train):,}, Val={len(c_val):,}, Test={len(c_test):,} -> {c_export_info['task_dir']}")
        pipeline_results["tasks"]["cancellation"] = {
            "metadata": c_dataset_meta.to_dict(),
            "export_info": c_export_info,
            "split_stats": c_splits,
        }

        # -------------------------------------------------------------
        # TASK C2: Cancellation Operational Landmark Risk (at t_allot + 5 min)
        # -------------------------------------------------------------
        print("\n" + "-" * 50)
        print("PROCESSING TASK C2: Operational Landmark Cancellation Risk (t_allot + 5m)")
        print("-" * 50)
        landmark_cohort_df, landmark_exclusions = self.target_builder.build_landmark_cancellation_target(
            df_with_all_features, landmark_offset_min=self.config.landmark_offset_min
        )
        landmark_matrix = self.dataset_builder.build_cancellation_landmark_matrix(landmark_cohort_df)

        cl_train, cl_val, cl_test, cl_splits = self.splitter.split(landmark_matrix)

        post_landmark_cancels = int((landmark_matrix["target_cancelled_post_landmark"] == 1).sum())
        post_landmark_fulfilled = int((landmark_matrix["target_cancelled_post_landmark"] == 0).sum())

        cl_target_meta = TargetMetadata(
            name="target_cancelled_post_landmark",
            task_type="BINARY_CLASSIFICATION",
            description="Binary indicator if order active at t_allot + 5min subsequently cancels before delivery",
            stats={
                "class_0_delivered": post_landmark_fulfilled,
                "class_1_cancelled_post_landmark": post_landmark_cancels,
                "positive_rate_pct": round(post_landmark_cancels / len(landmark_matrix) * 100, 4),
            },
        )

        cl_features_meta = (
            self.dataset_builder.get_order_time_feature_metadata()
            + self.dataset_builder.get_landmark_feature_metadata()
        )

        cl_dataset_meta = DatasetMetadata(
            task_name="cancellation/operational_landmark",
            prediction_point="t_allot + 5 min (Operational Dispatch Landmark)",
            eligible_cohort_description="Active orders at t_allot + 5min (excluding orders cancelled or delivered prior to landmark)",
            total_rows=len(landmark_matrix),
            train_rows=len(cl_train),
            val_rows=len(cl_val),
            test_rows=len(cl_test),
            features=[f.__dict__ for f in cl_features_meta],
            target=cl_target_meta.__dict__,
            exclusions_log=landmark_exclusions,
            leakage_exclusions=[
                "cancelled_time", "delivered_time", "pickup_time", "transit_duration_min"
            ],
            fitted_parameters=fitted_params,
        )

        cl_export_info = self.exporter.export_task_dataset(
            "cancellation/operational_landmark", cl_train, cl_val, cl_test, cl_dataset_meta
        )
        print(f"Task C2 Exported: Train={len(cl_train):,}, Val={len(cl_val):,}, Test={len(cl_test):,} -> {cl_export_info['task_dir']}")
        pipeline_results["tasks"]["cancellation_landmark"] = {
            "metadata": cl_dataset_meta.to_dict(),
            "export_info": cl_export_info,
            "split_stats": cl_splits,
        }

        elapsed = time.time() - start_time
        pipeline_results["execution_time_seconds"] = round(elapsed, 2)
        print("\n" + "=" * 70)
        print(f"PREPROCESSING PIPELINE COMPLETED IN {elapsed:.2f} SECONDS")
        print("=" * 70)

        return pipeline_results


if __name__ == "__main__":
    pipeline = PreprocessingPipeline()
    results = pipeline.run()
