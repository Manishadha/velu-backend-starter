from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from starlette.status import HTTP_413_CONTENT_TOO_LARGE

router = APIRouter()


class MediaItem(BaseModel):
    id: int
    filename: str
    content_type: str
    size: int


class LocationCreate(BaseModel):
    name: str
    latitude: float
    longitude: float


class Location(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float


_MAX_UPLOAD_SIZE = 1024 * 1024
_ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/pdf",
}


def _media_store(app: Any) -> Dict[str, Any]:
    if not hasattr(app.state, "media_items"):
        app.state.media_items = []
        app.state.media_next_id = 1
    return {
        "items": app.state.media_items,
        "next_id": "media_next_id",
    }


def _location_store(app: Any) -> Dict[str, Any]:
    if not hasattr(app.state, "locations"):
        app.state.locations = []
        app.state.locations_next_id = 1
    return {
        "items": app.state.locations,
        "next_id": "locations_next_id",
    }


@router.post("/v1/files/upload", response_model=MediaItem, status_code=status.HTTP_201_CREATED)
async def upload_file(request: Request, file: UploadFile = File(...)) -> MediaItem:  # type: ignore[call-arg]
    content = await file.read()
    size = len(content)
    if size > _MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=HTTP_413_CONTENT_TOO_LARGE,
            detail="file_too_large",
        )
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_media_type",
        )

    store = _media_store(request.app)
    items: List[Dict[str, Any]] = store["items"]
    next_attr = store["next_id"]
    next_id = getattr(request.app.state, next_attr)
    setattr(request.app.state, next_attr, next_id + 1)

    item = {
        "id": next_id,
        "filename": file.filename or "",
        "content_type": file.content_type or "",
        "size": size,
    }
    items.append(item)
    return MediaItem(**item)


@router.get("/v1/media", response_model=List[MediaItem])
def list_media(request: Request) -> List[MediaItem]:
    store = _media_store(request.app)
    items: List[Dict[str, Any]] = store["items"]
    return [MediaItem(**item) for item in items]


@router.get("/v1/media/{item_id}", response_model=MediaItem)
def get_media_item(request: Request, item_id: int) -> MediaItem:
    store = _media_store(request.app)
    items: List[Dict[str, Any]] = store["items"]
    for item in items:
        if item["id"] == item_id:
            return MediaItem(**item)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")


@router.post("/v1/locations", response_model=Location, status_code=status.HTTP_201_CREATED)
def create_location(request: Request, payload: LocationCreate) -> Location:
    if not (-90.0 <= payload.latitude <= 90.0 and -180.0 <= payload.longitude <= 180.0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_coordinates")

    store = _location_store(request.app)
    items: List[Dict[str, Any]] = store["items"]
    next_attr = store["next_id"]
    next_id = getattr(request.app.state, next_attr)
    setattr(request.app.state, next_attr, next_id + 1)

    item = {
        "id": next_id,
        "name": payload.name,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
    }
    items.append(item)
    return Location(**item)


@router.get("/v1/locations", response_model=List[Location])
def list_locations(request: Request) -> List[Location]:
    store = _location_store(request.app)
    items: List[Dict[str, Any]] = store["items"]
    return [Location(**item) for item in items]
