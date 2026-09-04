from typing import Optional
from fastapi import Request
from src.features.feature_builder import ProductionFeatureBuilder
from src.inference.predictor import CloudSensePredictor
from src.ingestion.state_store import StateStore

def get_feature_builder(request: Request) -> ProductionFeatureBuilder:
    return request.app.state.feature_builder

def get_predictor(request: Request) -> CloudSensePredictor:
    return request.app.state.predictor

def get_state_store(request: Request) -> StateStore:
    return request.app.state.state_store

def get_pipeline(request: Request):
    return request.app.state.pipeline
