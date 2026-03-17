from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import random
import string

from ..database import get_db
from ..models import RFIDTag
from ..schemas import RFIDTagCreate, RFIDTagUpdate, RFIDTag as RFIDTagSchema

router = APIRouter(
    prefix="/rfid",
    tags=["rfid"],
)

@router.post("/", response_model=RFIDTagSchema, status_code=status.HTTP_201_CREATED)
def create_rfid_tag(tag: RFIDTagCreate, db: Session = Depends(get_db)):
    existing_tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag.tag_id).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RFID tag with this ID already exists"
        )
    
    db_tag = RFIDTag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag

@router.get("/", response_model=List[RFIDTagSchema])
def read_rfid_tags(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tags = db.query(RFIDTag).offset(skip).limit(limit).all()
    return tags

@router.get("/{tag_id}", response_model=RFIDTagSchema)
def read_rfid_tag(tag_id: str, db: Session = Depends(get_db)):
    tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFID tag not found")
    return tag

@router.put("/{tag_id}", response_model=RFIDTagSchema)
def update_rfid_tag(tag_id: str, tag_update: RFIDTagUpdate, db: Session = Depends(get_db)):
    tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFID tag not found")
    
    update_data = tag_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)
    
    db.commit()
    db.refresh(tag)
    return tag

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rfid_tag(tag_id: str, db: Session = Depends(get_db)):
    tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFID tag not found")
    
    db.delete(tag)
    db.commit()
    return None

@router.post("/{tag_id}/scan")
def scan_rfid_tag(tag_id: str, db: Session = Depends(get_db)):
    tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
    if tag is None:
        # Auto-create tag if not exists
        tag = RFIDTag(tag_id=tag_id)
        db.add(tag)
    
    tag.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(tag)
    
    # Here you would add logic to trigger actions based on tag assignment
    # For example, if tag is assigned to an operator, log their presence
    # or if assigned to a machine, update machine status
    
    return {
        "tag_id": tag.tag_id,
        "assigned_to": tag.assigned_to,
        "last_seen": tag.last_seen,
        "action": "scanned"
    }


@router.post("/scan")
def simulate_rfid_scan(db: Session = Depends(get_db)):
    """Simulate an RFID scan by generating a random tag ID."""
    # In production, this would read from the RFID driver
    tag_id = "RFID-" + ''.join(random.choices(string.digits, k=8))
    
    # Check if tag exists
    tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
    if tag is None:
        tag = RFIDTag(tag_id=tag_id)
        db.add(tag)
    
    tag.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(tag)
    
    # For login simulation, assume tag is assigned to operator with ID 1
    # In real system, you would have a mapping of tag to user
    return {
        "access_token": "simulated_token",
        "user": {
            "id": 1,
            "username": "operator",
            "role": "operator"
        },
        "tag": {
            "tag_id": tag.tag_id,
            "assigned_to": tag.assigned_to,
            "last_seen": tag.last_seen
        }
    }