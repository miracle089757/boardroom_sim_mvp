"""Minimal boardroom simulation package."""

from boardroom_sim.config import BoardProcessConfig, ExperimentConfig, load_experiment_config
from boardroom_sim.models import BoardCase, SimulationResult
from boardroom_sim.process import BoardProcessController
from boardroom_sim.simulator import BoardroomSimulator

__all__ = [
    "BoardCase",
    "SimulationResult",
    "BoardroomSimulator",
    "ExperimentConfig",
    "BoardProcessConfig",
    "BoardProcessController",
    "load_experiment_config",
]
