"""Pydantic models for tax and facility profiles."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class TaxProfileBase(BaseModel):
    """Base tax profile fields."""
    name: str
    character_id: Optional[int] = None
    broker_fee_buy: Decimal = Field(default=Decimal("3.00"), ge=0, le=50)
    broker_fee_sell: Decimal = Field(default=Decimal("3.00"), ge=0, le=50)
    sales_tax: Decimal = Field(default=Decimal("3.60"), ge=0, le=50)
    is_default: bool = False


class TaxProfileCreate(TaxProfileBase):
    """Schema for creating a tax profile."""
    pass


class TaxProfileUpdate(BaseModel):
    """Schema for updating a tax profile."""
    name: Optional[str] = None
    broker_fee_buy: Optional[Decimal] = Field(default=None, ge=0, le=50)
    broker_fee_sell: Optional[Decimal] = Field(default=None, ge=0, le=50)
    sales_tax: Optional[Decimal] = Field(default=None, ge=0, le=50)
    is_default: Optional[bool] = None


class TaxProfile(TaxProfileBase):
    """Full tax profile with id and timestamps."""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FacilityProfileBase(BaseModel):
    """Base facility profile fields."""
    name: str
    system_id: int
    structure_type: str = "station"
    me_bonus: Decimal = Field(default=Decimal("0"), ge=0, le=10)
    te_bonus: Decimal = Field(default=Decimal("0"), ge=0, le=30)
    cost_bonus: Decimal = Field(default=Decimal("0"), ge=0, le=10)
    facility_tax: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    reaction_me_bonus: Decimal = Field(default=Decimal("0"), ge=0, le=10)
    reaction_te_bonus: Decimal = Field(default=Decimal("0"), ge=0, le=30)
    fuel_bonus: Decimal = Field(default=Decimal("0"), ge=0, le=50)


class FacilityProfileCreate(FacilityProfileBase):
    """Schema for creating a facility profile."""
    pass


class FacilityProfileUpdate(BaseModel):
    """Schema for updating a facility profile."""
    name: Optional[str] = None
    system_id: Optional[int] = None
    structure_type: Optional[str] = None
    me_bonus: Optional[Decimal] = None
    te_bonus: Optional[Decimal] = None
    cost_bonus: Optional[Decimal] = None
    facility_tax: Optional[Decimal] = None
    reaction_me_bonus: Optional[Decimal] = None
    reaction_te_bonus: Optional[Decimal] = None
    fuel_bonus: Optional[Decimal] = None


class FacilityProfile(FacilityProfileBase):
    """Full facility profile with id and timestamps."""
    id: int
    system_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SystemCostIndex(BaseModel):
    """System Cost Index from ESI."""
    system_id: int
    system_name: Optional[str] = None
    manufacturing_index: Decimal = Field(default=Decimal("0"))
    reaction_index: Decimal = Field(default=Decimal("0"))
    copying_index: Decimal = Field(default=Decimal("0"))
    invention_index: Decimal = Field(default=Decimal("0"))
    research_te_index: Decimal = Field(default=Decimal("0"))
    research_me_index: Decimal = Field(default=Decimal("0"))
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
