"""Controlled fault injection and evaluation support for the vGPU catalog."""

from vgpu_eval.faults import FaultClass, FaultInjection, inject_fault

__all__ = ["FaultClass", "FaultInjection", "inject_fault"]
