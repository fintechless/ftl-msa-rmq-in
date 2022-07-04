"""
Flask blueprint for MSA
"""

from ftl_msa_rmq_in.msa.blueprints.rmq_in import BLUEPRINT_RMQ_IN

__all__ = [BLUEPRINT_RMQ_IN]
