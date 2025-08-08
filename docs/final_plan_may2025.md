# Arctic Species API: Final Backend Implementation Plan

**May 2025**

This document outlines the step-by-step plan to finalize the new backend architecture and migrate from the `/rebuild` directory to a standalone production-ready application.

## 1. Project Reorganization (Week 1)

### 1.1. Directory Structure Finalization

```
arctic-species-api/
├── app/                     # Main application code
│   ├── api/                 # API endpoints
│   │   ├── __init__.py
│   │   ├── routes.py        # API route definitions
│   │   ├── validators.py    # Request validation
│   │   └── responses.py     # Response formatting
│   ├── core/                # Core business logic
│   │   ├── __init__.py
│   │   ├── species.py       # Species handling
│   │   ├── trade_data.py    # Trade data processing
│   │   └── iucn.py          # IUCN data integration
│   ├── data/                # Data management
│   │   ├── __init__.py
│   │   ├── models.py        # Data models
│   │   ├── repositories.py  # Database operations
│   │   └── migrations/      # Database migrations
│   ├── utils/               # Utilities
│   │   ├── __init__.py
│   │   ├── logging.py       # Logging utilities
│   │   └── validators.py    # Data validation
│   └── __init__.py
├── config/                  # Configuration
│   ├── __init__.py
│   ├── settings.py          # Application settings
│   ├── database.py          # Database configuration
│   └── .env                 # Environment variables (gitignored)
├── docs/                    # Documentation
│   ├── api_docs.md          # API documentation
│   ├── schemas/             # Data schema docs
│   └── reports/             # Analysis reports
├── scripts/                 # Utility scripts
│   ├── data_processing/     # ETL scripts
│   │   ├── extract.py
│   │   ├── transform.py
│   │   └── load.py
│   └── maintenance/         # Maintenance scripts
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── fixtures/            # Test fixtures
├── .gitignore               # Git ignore file
├── requirements.txt         # Python dependencies
├── README.md                # Project overview
└── main.py                  # Application entry point
```

### 1.2. File Migration Strategy

1. **Preserve Data Files**:
   - Copy all optimized data files to the new structure
   - Verify data integrity after migration

2. **Refactor Core Components**:
   - Split monolithic scripts into modular components
   - Move database operations to repositories
   - Convert utility functions to proper modules

3. **Migration Checklist**:
   - [ ] Create new directory structure
   - [ ] Move configuration files
   - [ ] Migrate core business logic
   - [ ] Create dedicated API layer
   - [ ] Establish data models and repositories
   - [ ] Set up testing infrastructure

## 2. Code Modularization (Week 2)

### 2.1. Core Module Development

1. **Species Module**:
   - Create `Species` class with full CRUD operations
   - Implement taxonomic hierarchy handling
   - Add IUCN integration methods

```python
# app/core/species.py
from app.data.repositories import SpeciesRepository

class Species:
    def __init__(self, repository=None):
        self.repository = repository or SpeciesRepository()
    
    def get_by_scientific_name(self, name):
        return self.repository.find_by_scientific_name(name)
        
    def get_with_trade_summary(self, species_id):
        species = self.repository.find_by_id(species_id)
        if not species:
            return None
            
        trade_summary = self.repository.get_trade_summary(species_id)
        species['trade_summary'] = trade_summary
        return species
```

2. **Trade Data Module**:
   - Create `TradeData` class for accessing trade records
   - Implement filtering and aggregation methods
   - Add data validation and transformation

```python
# app/core/trade_data.py
from app.data.repositories import TradeRepository
from app.utils.validators import validate_trade_filters

class TradeData:
    def __init__(self, repository=None):
        self.repository = repository or TradeRepository()
    
    def get_records(self, filters=None, limit=100, offset=0):
        # Validate filters
        validated_filters = validate_trade_filters(filters or {})
        
        # Get records with filters
        return self.repository.find_records(
            filters=validated_filters,
            limit=limit,
            offset=offset
        )
    
    def get_summary_by_year(self, species_id=None, start_year=None, end_year=None):
        return self.repository.aggregate_by_year(
            species_id=species_id,
            start_year=start_year,
            end_year=end_year
        )
```

3. **IUCN Module**:
   - Create `IUCN` class for Red List integration
   - Implement assessment retrieval and processing
   - Add caching mechanisms

### 2.2. Repository Layer Development

1. **Repository Interfaces**:
   - Create base repository pattern
   - Implement database operations for each entity
   - Add transaction support and error handling

```python
# app/data/repositories.py
from app.config.database import get_db_client

class SpeciesRepository:
    def __init__(self, db_client=None):
        self.db = db_client or get_db_client()
    
    def find_all(self, limit=100, offset=0):
        return self.db.table('species').select('*').limit(limit).offset(offset).execute().data
    
    def find_by_id(self, species_id):
        result = self.db.table('species').select('*').eq('id', species_id).execute()
        return result.data[0] if result.data else None
    
    def find_by_scientific_name(self, name):
        result = self.db.table('species').select('*').eq('scientific_name', name).execute()
        return result.data[0] if result.data else None
    
    def get_trade_summary(self, species_id):
        # Get trade summary for species
        return self.db.table('cites_trade_records')
                  .select('year, COUNT(*) as record_count, SUM(quantity) as total_quantity')
                  .eq('species_id', species_id)
                  .group('year')
                  .order('year')
                  .execute().data
```

2. **Data Models**:
   - Define Pydantic models for all entities
   - Implement validation and serialization
   - Add type hints and documentation

```python
# app/data/models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import date

class Species(BaseModel):
    id: UUID
    scientific_name: str
    common_name: Optional[str] = None
    class_name: str
    order_name: str
    family: str
    genus: str
    iucn_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "scientific_name": "Ursus maritimus",
                "common_name": "Polar Bear",
                "class_name": "Mammalia",
                "order_name": "Carnivora",
                "family": "Ursidae",
                "genus": "Ursus",
                "iucn_id": "22823"
            }
        }
```

## 3. API Development (Week 3)

### 3.1. API Endpoints

1. **Species Endpoints**:
   - `GET /api/species`: List all species
   - `GET /api/species/{id}`: Get species by ID
   - `GET /api/species/{id}/trade`: Get species trade data

2. **Trade Data Endpoints**:
   - `GET /api/trade`: Query trade records
   - `GET /api/trade/summary`: Get trade summary stats
   - `GET /api/trade/years`: Get year range and counts

3. **IUCN Endpoints**:
   - `GET /api/iucn/assessments/{species_id}`: Get IUCN assessments
   - `GET /api/iucn/status/{species_id}`: Get current IUCN status

### 3.2. API Framework

1. **FastAPI Implementation**:
   - Set up FastAPI application
   - Implement route handlers
   - Add request validation
   - Configure CORS and middleware

```python
# app/api/routes.py
from fastapi import APIRouter, Depends, Query, Path, HTTPException
from typing import Optional, List

from app.core.species import Species
from app.core.trade_data import TradeData
from app.data.models import SpeciesModel, TradeRecordModel

router = APIRouter()

@router.get("/species", response_model=List[SpeciesModel])
async def list_species(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    species_service = Species()
    return species_service.get_all(limit=limit, offset=offset)

@router.get("/species/{species_id}", response_model=SpeciesModel)
async def get_species(
    species_id: UUID = Path(..., description="The UUID of the species")
):
    species_service = Species()
    species = species_service.get_by_id(species_id)
    
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")
        
    return species

@router.get("/species/{species_id}/trade")
async def get_species_trade(
    species_id: UUID = Path(..., description="The UUID of the species"),
    start_year: Optional[int] = Query(None, ge=1975, le=2025),
    end_year: Optional[int] = Query(None, ge=1975, le=2025),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    trade_service = TradeData()
    return trade_service.get_records(
        filters={"species_id": str(species_id), "year_gte": start_year, "year_lte": end_year},
        limit=limit,
        offset=offset
    )
```

### 3.3. API Documentation

1. **OpenAPI Integration**:
   - Configure automatic OpenAPI documentation
   - Add detailed method descriptions
   - Include example requests and responses

2. **Manual Documentation**:
   - Create comprehensive API usage guide
   - Document authentication and rate limiting
   - Provide example use cases

## 4. Database Finalization (Week 4)

### 4.1. Database Migration Scripts

1. **Schema Definition**:
   - Create finalized database schema
   - Set up proper indexes and constraints
   - Implement referential integrity

2. **Migration Scripts**:
   - Create scripts for clean database setup
   - Add data migration utilities
   - Implement rollback capabilities

```python
# scripts/db_setup.py
import sys
from pathlib import Path
from app.config.database import get_db_client

def setup_database():
    """Set up the database schema from scratch"""
    db = get_db_client()
    
    print("Creating database schema...")
    
    # Create species table
    db.table("species").create({
        "id": "uuid primary key",
        "scientific_name": "text not null unique",
        "common_name": "text",
        "class_name": "text not null",
        "order_name": "text not null",
        "family": "text not null",
        "genus": "text not null",
        "iucn_id": "text",
        "created_at": "timestamptz default now()",
        "updated_at": "timestamptz default now()"
    })
    
    # Create trade records table
    # ...additional table creation...
    
    # Create necessary indexes
    db.execute_sql("CREATE INDEX idx_species_scientific_name ON species(scientific_name)")
    db.execute_sql("CREATE INDEX idx_trade_records_species_id ON cites_trade_records(species_id)")
    db.execute_sql("CREATE INDEX idx_trade_records_year ON cites_trade_records(year)")
    
    print("Database schema created successfully")
```

### 4.2. Data Migration

1. **Optimized Data Loading**:
   - Refine data loading scripts
   - Implement transaction-safe loading
   - Create progress tracking and validation

2. **Data Integrity Checks**:
   - Implement comprehensive validation
   - Add database-level constraints
   - Create data quality reports

## 5. Testing Framework (Week 5)

### 5.1. Unit Tests

1. **Test Coverage**:
   - Implement tests for all core modules
   - Add repository layer tests
   - Create API endpoint tests

2. **Test Utilities**:
   - Create test fixtures and factories
   - Implement database mocking
   - Add test configuration

```python
# tests/unit/test_species.py
import pytest
from unittest.mock import MagicMock
from app.core.species import Species
from uuid import uuid4

def test_get_by_scientific_name():
    # Arrange
    mock_repo = MagicMock()
    mock_species = {
        "id": str(uuid4()),
        "scientific_name": "Ursus maritimus",
        "common_name": "Polar Bear"
    }
    mock_repo.find_by_scientific_name.return_value = mock_species
    
    species_service = Species(repository=mock_repo)
    
    # Act
    result = species_service.get_by_scientific_name("Ursus maritimus")
    
    # Assert
    assert result == mock_species
    mock_repo.find_by_scientific_name.assert_called_once_with("Ursus maritimus")
```

### 5.2. Integration Tests

1. **API Integration Tests**:
   - Test all API endpoints
   - Verify response formats
   - Test error handling

2. **Database Integration**:
   - Test database operations
   - Verify data integrity
   - Test transaction management

### 5.3. Performance Tests

1. **Load Testing**:
   - Test API performance under load
   - Identify bottlenecks
   - Establish performance baselines

2. **Optimization**:
   - Implement performance improvements
   - Add caching where appropriate
   - Optimize database queries

## 6. Deployment Configuration (Week 6)

### 6.1. Containerization

1. **Docker Setup**:
   - Create Docker file
   - Configure Docker Compose for local development
   - Set up multi-stage builds

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Production image
FROM base as production
ENV ENVIRONMENT=production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development image
FROM base as development
ENV ENVIRONMENT=development
RUN pip install pytest pytest-cov
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

2. **CI/CD Configuration**:
   - Set up GitHub Actions workflows
   - Implement automated testing
   - Configure deployment pipelines

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, development ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=app tests/
```

### 6.2. Environment Configuration

1. **Configuration Management**:
   - Implement environment-based configs
   - Set up secure credential management
   - Create deployment profiles

2. **Monitoring Setup**:
   - Configure logging and metrics
   - Set up error tracking
   - Implement performance monitoring

## 7. Documentation & Handover (Week 7)

### 7.1. Technical Documentation

1. **Architecture Documentation**:
   - Create detailed system architecture docs
   - Document database schema
   - Create API reference documentation

2. **Developer Guide**:
   - Create setup and onboarding guide
   - Document development workflow
   - Add troubleshooting section

### 7.2. User Documentation

1. **API Usage Guide**:
   - Document all API endpoints
   - Provide example requests and responses
   - Create user authentication guide

2. **Data Guide**:
   - Document data structure and relationships
   - Create data dictionary
   - Provide data interpretation guide

## Implementation Timeline

| Week | Focus | Deliverables |
|------|-------|-------------|
| 1 | Project Reorganization | Directory structure, file migration |
| 2 | Code Modularization | Core modules, repositories, data models |
| 3 | API Development | API endpoints, documentation |
| 4 | Database Finalization | Migration scripts, data loading |
| 5 | Testing Framework | Unit tests, integration tests |
| 6 | Deployment Configuration | Docker, CI/CD |
| 7 | Documentation & Handover | Tech docs, user guides |

## Migration Checklist

- [ ] Create new directory structure
- [ ] Set up dependency management
- [ ] Migrate core logic with refactoring
- [ ] Implement repository pattern
- [ ] Create API layer
- [ ] Set up database schema
- [ ] Migrate optimized data
- [ ] Implement comprehensive tests
- [ ] Configure deployment
- [ ] Complete documentation

---

*This plan was created on May 24, 2025, and outlines the final steps to transition the Arctic Species API from the rebuild prototype to the production-ready backend system.*