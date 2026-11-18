from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.database.session import get_db
from backend.app.models.restaurant import Restaurant
from backend.app.models.historical_order import HistoricalOrder
from backend.app.services.ingestion.restaurant_loader import RestaurantDatasetLoader
from backend.app.services.ingestion.order_history_loader import OrderHistoryDatasetLoader
from backend.app.core.exceptions import ValidationError

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.get("/status", response_model=Dict[str, Any])
def get_ingestion_status(db: Session = Depends(get_db)):
    """Summary of ingested public historical records and provenance breakdown."""
    hist_restaurants_count = db.scalar(
        select(func.count(Restaurant.id)).where(Restaurant.data_source == "PUBLIC_HISTORICAL")
    ) or 0
    synth_restaurants_count = db.scalar(
        select(func.count(Restaurant.id)).where(Restaurant.data_source == "SYNTHETIC")
    ) or 0
    hist_orders_count = db.scalar(select(func.count(HistoricalOrder.id))) or 0

    return {
        "status": "ready",
        "provenance": {
            "PUBLIC_HISTORICAL": {
                "restaurants_count": hist_restaurants_count,
                "historical_orders_count": hist_orders_count,
                "huggingface_dataset_id": RestaurantDatasetLoader.DATASET_ID,
                "kaggle_dataset_id": OrderHistoryDatasetLoader.DATASET_ID,
            },
            "SYNTHETIC": {
                "restaurants_count": synth_restaurants_count,
            },
        },
    }


@router.post("/restaurants", response_model=Dict[str, Any])
async def ingest_restaurants(
    file: Optional[UploadFile] = File(None, description="Optional uploaded CSV file"),
    use_local_or_hf: bool = Query(True, description="Ingest from data/raw/restaurants/ or Hugging Face"),
    limit: Optional[int] = Query(None, description="Max rows to ingest (optional)"),
    db: Session = Depends(get_db),
):
    """
    Ingest Swiggy restaurant dataset from Hugging Face or raw CSV.
    Preserves exact provenance (PUBLIC_HISTORICAL) and original listing values.
    """
    loader = RestaurantDatasetLoader(db)
    temp_path = None

    if file and file.filename:
        if not file.filename.endswith(".csv"):
            raise ValidationError("Uploaded file must be a .csv file")
        temp_path = f"data/raw/restaurants/uploaded_{file.filename}"
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

    report = loader.ingest(filepath=temp_path, limit=limit)

    return {
        "success": True,
        "message": f"Ingested {report.inserted_count} restaurants into database",
        "data_quality_report": report.summary(),
    }


@router.post("/orders/history", response_model=Dict[str, Any])
def ingest_order_history(
    limit: Optional[int] = Query(1000, description="Max historical rows to ingest (default: 1000 for safety)"),
    db: Session = Depends(get_db),
):
    """
    Ingest historical order lifecycle telemetry from data/raw/orders/Rider-Info.csv.
    Strictly isolated into historical_orders table. Never mixed with live synthetic orders.
    """
    loader = OrderHistoryDatasetLoader(db)
    report = loader.ingest(limit=limit)

    return {
        "success": True,
        "message": f"Ingested {report.inserted_count} historical orders into historical_orders table",
        "data_quality_report": report.summary(),
    }
