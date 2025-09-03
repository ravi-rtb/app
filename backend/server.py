from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Loco Data Summary API", description="API for locomotive data summary and analysis")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Google Sheets configuration
SHEET_ID = '1oVY3a7LrG4zn2oVkW88bi31uZqGdw_mb-YHk2-NVqKQ'
SHEET_NAMES = {
    'loco_list': 'Loco_list',
    'loco_schedules': 'Loco_Schedules', 
    'traction_failures': 'Traction_failures',
    'wag7_modifications': 'WAG7_Modifications'
}

# Data refresh settings
REFRESH_INTERVAL_HOURS = 6
last_refresh_time = None

# Define Models
class LocoDetail(BaseModel):
    field: str
    value: str

class LocoSchedule(BaseModel):
    incoming_date: Optional[str] = None
    sch: Optional[str] = None
    outgoing_date: Optional[str] = None

class TractionFailure(BaseModel):
    date_failed: Optional[str] = None
    icms_message: Optional[str] = None
    loco_no: Optional[str] = None
    mu_with: Optional[str] = None
    div: Optional[str] = None
    rly: Optional[str] = None
    brief_message: Optional[str] = None
    cause_of_failure: Optional[str] = None
    component: Optional[str] = None
    system: Optional[str] = None

class LocoSummaryResponse(BaseModel):
    loco_no: str
    details: List[LocoDetail]
    schedules: List[LocoSchedule]
    failures: List[TractionFailure]
    modifications: List[ModificationDetail]
    last_updated: datetime

class RefreshStatusResponse(BaseModel):
    status: str
    last_refresh: Optional[datetime] = None
    next_refresh: Optional[datetime] = None
    records_count: Dict[str, int]

# Utility Functions
def clean_dataframe(df):
    """Clean dataframe by handling NaN values and converting to string"""
    return df.fillna('').astype(str)

async def fetch_sheet_data(sheet_name: str) -> pd.DataFrame:
    """Fetch data from Google Sheets and return as DataFrame"""
    try:
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
        df = pd.read_csv(url)
        return clean_dataframe(df)
    except Exception as e:
        logger.error(f"Error fetching {sheet_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch {sheet_name} data")

async def refresh_all_data():
    """Refresh all data from Google Sheets and store in MongoDB"""
    global last_refresh_time
    
    try:
        logger.info("Starting data refresh from Google Sheets...")
        
        # Clear existing data
        await db.loco_data.delete_many({})
        await db.schedule_data.delete_many({})
        await db.failure_data.delete_many({})
        
        # Fetch and store Loco_list data
        loco_df = await fetch_sheet_data(SHEET_NAMES['loco_list'])
        loco_records = []
        for _, row in loco_df.iterrows():
            record = {
                'collection': 'loco_data',
                'loco_no': str(row.get('Loco No.', '')).strip(),
                'data': row.to_dict(),
                'updated_at': datetime.utcnow()
            }
            loco_records.append(record)
        
        if loco_records:
            await db.loco_data.insert_many(loco_records)
        
        # Fetch and store Loco_Schedules data
        schedule_df = await fetch_sheet_data(SHEET_NAMES['loco_schedules'])
        schedule_records = []
        for _, row in schedule_df.iterrows():
            # Clean loco number (remove .0 if present)
            loco_no = str(row.get('Loco No. ', '')).replace('.0', '').strip()
            record = {
                'collection': 'schedule_data',
                'loco_no': loco_no,
                'data': row.to_dict(),
                'updated_at': datetime.utcnow()
            }
            schedule_records.append(record)
        
        if schedule_records:
            await db.schedule_data.insert_many(schedule_records)
        
        # Fetch and store Traction_failures data  
        failure_df = await fetch_sheet_data(SHEET_NAMES['traction_failures'])
        failure_records = []
        for _, row in failure_df.iterrows():
            # Clean loco number (remove .0 if present)
            loco_no = str(row.get('LOCO No. ', '')).replace('.0', '').strip()
            record = {
                'collection': 'failure_data',
                'loco_no': loco_no,
                'data': row.to_dict(),
                'updated_at': datetime.utcnow()
            }
            failure_records.append(record)
        
        if failure_records:
            await db.failure_data.insert_many(failure_records)
        
        # Fetch and store WAG7_Modifications data
        modifications_df = await fetch_sheet_data(SHEET_NAMES['wag7_modifications'])
        modifications_records = []
        for _, row in modifications_df.iterrows():
            record = {
                'collection': 'modifications_data',
                'loco_no': str(row.get('Loco No.', '')).strip(),  # Adjust column name as in your sheet
                'data': row.to_dict(),
                'updated_at': datetime.utcnow()
            }
            modifications_records.append(record)
        if modifications_records:
            await db.modifications_data.insert_many(modifications_records)
            
        last_refresh_time = datetime.utcnow()
        
        logger.info(f"Data refresh completed. Loco: {len(loco_records)}, Schedules: {len(schedule_records)}, Failures: {len(failure_records)}")
        
        return {
            'loco_data': len(loco_records),
            'schedule_data': len(schedule_records),
            'failure_data': len(failure_records)
        }
        
    except Exception as e:
        logger.error(f"Error during data refresh: {e}")
        raise e

async def check_and_refresh_data():
    """Check if data needs refresh and refresh if necessary"""
    global last_refresh_time
    
    if (last_refresh_time is None or 
        datetime.utcnow() - last_refresh_time > timedelta(hours=REFRESH_INTERVAL_HOURS)):
        await refresh_all_data()

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Loco Data Summary API", "version": "1.0.0"}

@api_router.get("/loco/{loco_no}", response_model=LocoSummaryResponse)
async def get_loco_summary(loco_no: str):
    """Get comprehensive loco summary including details, schedules, and failures"""
    
    # Ensure data is fresh
    await check_and_refresh_data()
    
    # Clean the input loco number
    loco_no = str(loco_no).strip()
    
    # Fetch loco details (exclude Type column)
    loco_data = await db.loco_data.find_one({'loco_no': loco_no})
    details = []
    
    if loco_data and 'data' in loco_data:
        data = loco_data['data']
        exclude_fields = ['Type', 'Loco No.']
        
        for key, value in data.items():
            if key not in exclude_fields and str(value).strip():
                details.append(LocoDetail(field=key, value=str(value)))
    
    # Fetch loco schedules
    schedule_records = await db.schedule_data.find({'loco_no': loco_no}).to_list(1000)
    schedules = []
    
    for record in schedule_records:
        if 'data' in record:
            data = record['data']
            schedule = LocoSchedule(
                incoming_date=str(data.get('Incoming Date ', '')).strip() or None,
                sch=str(data.get('Sch ', '')).strip() or None,
                outgoing_date=str(data.get('Outgoing Date ', '')).strip() or None
            )
            schedules.append(schedule)
    
    # Fetch traction failures
    failure_records = await db.failure_data.find({'loco_no': loco_no}).to_list(1000)
    failures = []
    
    for record in failure_records:
        if 'data' in record:
            data = record['data']
            failure = TractionFailure(
                date_failed=str(data.get('Date Failed ', '')).strip() or None,
                icms_message=str(data.get('ICMS/ Message ', '')).strip() or None,
                loco_no=str(data.get('LOCO No. ', '')).strip() or None,
                mu_with=str(data.get('MU with ', '')).strip() or None,
                div=str(data.get('Div ', '')).strip() or None,
                rly=str(data.get('Rly ', '')).strip() or None,
                brief_message=str(data.get('Brief Message ', '')).strip() or None,
                cause_of_failure=str(data.get('Cause of Failure ', '')).strip() or None,
                component=str(data.get('Component ', '')).strip() or None,
                system=str(data.get('System ', '')).strip() or None
            )
            failures.append(failure)
    # Fetch modifications
    modifications_data = await db.modifications_data.find_one({'loco_no': loco_no})
    modifications = []
    if modifications_data and 'data' in modifications_data:
        data = modifications_data['data']
        exclude_fields = ['Type', 'Loco No.']  # adjust as needed
        for key, value in data.items():
            if key not in exclude_fields and str(value).strip():
                modifications.append(ModificationDetail(field=key, value=str(value)))
            
    
   # If there's no data at all, throw 404
    if not details and not schedules and not failures and not modifications:
        raise HTTPException(status_code=404, detail=f"No data found for loco number: {loco_no}")

    return LocoSummaryResponse(
        loco_no=loco_no,
        details=details,
        schedules=schedules,
        failures=failures,
        modifications=modifications,
        last_updated=last_refresh_time or datetime.utcnow()
    )

@api_router.post("/refresh")
async def manual_refresh():
    """Manually trigger data refresh from Google Sheets"""
    try:
        counts = await refresh_all_data()
        return {
            "status": "success",
            "message": "Data refreshed successfully",
            "counts": counts,
            "refreshed_at": last_refresh_time
        }
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@api_router.get("/status", response_model=RefreshStatusResponse)
async def get_refresh_status():
    """Get data refresh status and statistics"""
    
    # Get record counts
    loco_count = await db.loco_data.count_documents({})
    schedule_count = await db.schedule_data.count_documents({})
    failure_count = await db.failure_data.count_documents({})
    modifications_count = await db.modifications_data.count_documents({})
    
    next_refresh = None
    if last_refresh_time:
        next_refresh = last_refresh_time + timedelta(hours=REFRESH_INTERVAL_HOURS)
    
    return RefreshStatusResponse(
        status="active" if last_refresh_time else "pending",
        last_refresh=last_refresh_time,
        next_refresh=next_refresh,
        records_count={
            "loco_data": loco_count,
            "schedule_data": schedule_count,
            "failure_data": failure_count,
            "modifications_data": modifications_count
        }
    )

@api_router.get("/search/{partial_loco_no}")
async def search_locos(partial_loco_no: str):
    """Search for locos by partial loco number"""
    await check_and_refresh_data()
    
    # Search for matching loco numbers
    pipeline = [
        {"$match": {"loco_no": {"$regex": f".*{partial_loco_no}.*", "$options": "i"}}},
        {"$group": {"_id": "$loco_no"}},
        {"$sort": {"_id": 1}},
        {"$limit": 20}
    ]
    
    results = await db.loco_data.aggregate(pipeline).to_list(20)
    loco_numbers = [result["_id"] for result in results if result["_id"].strip()]
    
    return {"suggestions": loco_numbers}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    logger.info("Starting up Loco Data Summary API...")
    try:
        await refresh_all_data()
        logger.info("Initial data refresh completed")
    except Exception as e:
        logger.error(f"Failed to refresh data on startup: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
