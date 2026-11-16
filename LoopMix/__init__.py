from __future__ import absolute_import


def create_instance(c_instance):
    # Imported here so logic.py can be tested without Live's _Framework.
    from .loop_mix import LoopMix
    return LoopMix(c_instance)
