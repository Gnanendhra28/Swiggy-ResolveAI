import os
import json
import time
from typing import Dict, Any

from backend.app.ml.models.config import (
    get_task_a_config,
    get_task_b_config,
    get_task_c1_config,
    get_task_c2_config,
)
from backend.app.ml.models.trainer import ModelTrainer
from backend.app.ml.models.registry import ModelRegistry


def run_baseline_training() -> Dict[str, Any]:
    print("=" * 80)
    print("SWIGGY RESOLVEAI — PHASE 2.3 BASELINE MODEL DEVELOPMENT PIPELINE")
    print("=" * 80)
    t_start = time.time()

    registry = ModelRegistry("data/artifacts/models")
    summary = {
        "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "tasks": {},
    }

    # 1. TASK A: Delivery Duration Regression
    cfg_a = get_task_a_config()
    trainer_a = ModelTrainer(cfg_a, registry)
    res_a = trainer_a.train_regression_task()
    summary["tasks"]["task_a_delivery_duration"] = res_a

    # 2. TASK B: Allocation Delay Classification
    cfg_b = get_task_b_config()
    trainer_b = ModelTrainer(cfg_b, registry)
    res_b = trainer_b.train_classification_task()
    summary["tasks"]["task_b_allocation_delay"] = res_b

    # 3. TASK C1: Upfront Cancellation Classification
    cfg_c1 = get_task_c1_config()
    trainer_c1 = ModelTrainer(cfg_c1, registry)
    res_c1 = trainer_c1.train_classification_task()
    summary["tasks"]["task_c1_cancellation_upfront"] = res_c1

    # 4. TASK C2: Operational Landmark Cancellation Classification
    cfg_c2 = get_task_c2_config()
    trainer_c2 = ModelTrainer(cfg_c2, registry)
    res_c2 = trainer_c2.train_classification_task()
    summary["tasks"]["task_c2_cancellation_landmark"] = res_c2

    t_total = time.time() - t_start
    summary["total_training_duration_seconds"] = round(t_total, 2)

    summary_path = os.path.join("data/artifacts/models", "summary_evaluation.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print(f"ALL 4 BASELINE MODELING TASKS COMPLETED IN {t_total:.2f} SECONDS")
    print(f"Summary persisted to: {summary_path}")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    run_baseline_training()
