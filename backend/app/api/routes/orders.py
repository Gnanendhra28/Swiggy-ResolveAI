import math
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.order import OrderSummaryResponse, OrderDetailResponse
from backend.app.schemas.order_event import OrderEventResponse
from backend.app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/metrics", response_model=Dict[str, Any])
def get_order_metrics(db: Session = Depends(get_db)):
    """Retrieve operational dashboard summary metrics."""
    return OrderService.get_dashboard_metrics(db)


@router.get("", response_model=PaginatedResponse[OrderSummaryResponse])
def list_orders(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by order status"),
    demo_run_id: Optional[str] = Query(default=None, description="Filter by simulation demo_run_id"),
    data_source: Optional[str] = Query(default=None, description="Filter by data source (SYNTHETIC/HISTORICAL_DATASET)"),
    search: Optional[str] = Query(default=None, description="Search by order ID, customer, restaurant, or city"),
    db: Session = Depends(get_db),
):
    """Retrieve a paginated list of orders with optional filtering and search."""
    items, total = OrderService.list_orders(
        db=db,
        page=page,
        limit=limit,
        status=status,
        demo_run_id=demo_run_id,
        data_source=data_source,
        search=search,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedResponse[OrderSummaryResponse](
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order_details(
    order_id: str = Path(..., description="Order UUID or external_order_id"),
    db: Session = Depends(get_db),
):
    """Retrieve complete order details including customer, restaurant, rider, and events."""
    return OrderService.get_order_by_id(db=db, order_id=order_id)


@router.get("/{order_id}/events", response_model=List[OrderEventResponse])
def get_order_events(
    order_id: str = Path(..., description="Order UUID or external_order_id"),
    db: Session = Depends(get_db),
):
    """Retrieve chronological event history for an order."""
    return OrderService.get_order_events(db=db, order_id=order_id)
