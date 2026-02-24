"""
Financial Types with Strict Decimal Validation

This module defines strict financial types using Decimal to prevent
precision loss from float conversion. All financial values must be
provided as strings and will be converted to Decimal.
"""

from decimal import Decimal, InvalidOperation
from typing import Union, Annotated, Any
from pydantic import (
    BaseModel, 
    Field, 
    GetPydanticSchema,
    ConfigDict,
    field_validator
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class DecimalString:
    """
    Custom type that accepts string values and converts them to Decimal.
    Prevents float precision loss by requiring string input.
    """
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetPydanticSchema
    ) -> core_schema.CoreSchema:
        return core_schema.chain_schema([
            core_schema.union_schema([
                core_schema.str_schema(),
                core_schema.decimal_schema()
            ]),
            core_schema.no_info_plain_validator_function(cls.validate)
        ])
    
    @classmethod
    def validate(cls, value: Union[str, Decimal]) -> Decimal:
        """Validate and convert input to Decimal"""
        if isinstance(value, Decimal):
            return value
        
        if isinstance(value, str):
            try:
                # Remove any whitespace and validate format
                value = value.strip()
                if not value:
                    raise ValueError("Empty string cannot be converted to Decimal")
                
                # Validate that string represents a valid number
                try:
                    float(value)  # Quick validation
                except ValueError:
                    raise ValueError(f"Invalid numeric string: {value}")
                
                return Decimal(value)
            except InvalidOperation as e:
                raise ValueError(f"Invalid decimal format: {value}") from e
        
        raise ValueError(f"Expected string or Decimal, got {type(value)}")


class MonetaryAmount(BaseModel):
    """
    Strict monetary amount with Decimal precision.
    Must be provided as string to prevent float precision loss.
    """
    model_config = ConfigDict(strict=True)
    
    amount: Annotated[Decimal, DecimalString] = Field(
        ..., 
        description="Monetary amount as string (e.g., '123.45')",
        min_digits=0
    )
    currency: str = Field(
        ..., 
        pattern=r'^[A-Z]{3}$',
        description="ISO 4217 currency code (e.g., 'USD')"
    )
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate monetary amount is non-negative"""
        if v < 0:
            raise ValueError("Monetary amount cannot be negative")
        return v
    
    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"


class Price(BaseModel):
    """
    Strict price type with Decimal precision.
    Accepts only string input to prevent float conversion.
    """
    model_config = ConfigDict(strict=True)
    
    value: Annotated[Decimal, DecimalString] = Field(
        ..., 
        description="Price value as string (e.g., '123.45')",
        gt=Decimal('0')
    )
    currency: str = Field(
        ..., 
        pattern=r'^[A-Z]{3}$',
        description="ISO 4217 currency code"
    )
    
    def __str__(self) -> str:
        return f"{self.value} {self.currency}"


class Volume(BaseModel):
    """
    Strict volume type with Decimal precision for fractional shares.
    Accepts only string input to prevent float conversion.
    """
    model_config = ConfigDict(strict=True)
    
    value: Annotated[Decimal, DecimalString] = Field(
        ..., 
        description="Volume value as string (e.g., '1000.5')",
        gt=Decimal('0')
    )
    unit: str = Field(
        default="shares",
        description="Volume unit (e.g., 'shares', 'contracts', 'coins')"
    )
    
    def __str__(self) -> str:
        return f"{self.value} {self.unit}"


class Percentage(BaseModel):
    """
    Strict percentage type with Decimal precision.
    Accepts only string input to prevent float conversion.
    """
    model_config = ConfigDict(strict=True)
    
    value: Annotated[Decimal, DecimalString] = Field(
        ..., 
        description="Percentage value as string (e.g., '0.05' for 5%)",
        ge=Decimal('-1'),
        le=Decimal('1')
    )
    
    def as_decimal(self) -> Decimal:
        """Return percentage as decimal (e.g., 0.05 for 5%)"""
        return self.value
    
    def as_percentage(self) -> Decimal:
        """Return percentage as percentage (e.g., 5.0 for 5%)"""
        return self.value * Decimal('100')
    
    def __str__(self) -> str:
        return f"{self.as_percentage():.2f}%"


# Type aliases for common usage
StrictDecimal = Annotated[Decimal, DecimalString]
PriceString = Annotated[str, Field(pattern=r'^\d+(\.\d+)?$')]
VolumeString = Annotated[str, Field(pattern=r'^\d+(\.\d+)?$')]


# Utility functions for working with strict financial types
def create_price(value: Union[str, Decimal], currency: str) -> Price:
    """Factory function to create Price with validation"""
    if isinstance(value, Decimal):
        value_str = str(value)
    else:
        value_str = value
    
    return Price(value=value_str, currency=currency)


def create_volume(value: Union[str, Decimal], unit: str = "shares") -> Volume:
    """Factory function to create Volume with validation"""
    if isinstance(value, Decimal):
        value_str = str(value)
    else:
        value_str = value
    
    return Volume(value=value_str, unit=unit)


def create_percentage(value: Union[str, Decimal, float]) -> Percentage:
    """Factory function to create Percentage with validation"""
    if isinstance(value, float):
        raise ValueError("Float not allowed for Percentage. Use string or Decimal.")
    
    if isinstance(value, Decimal):
        value_str = str(value)
    else:
        value_str = value
    
    return Percentage(value=value_str)
