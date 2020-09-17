import pytest
from collections import namedtuple
from lenses import lens

LensCollection = namedtuple(
    'LensCollection', ('raw', 'intermediate', 'final'))


@pytest.fixture
def sprint_history_lenses():
    sprint = LensCollection(
        lens['changelog']['histories'],
        lens['sprint_history'],
        lens.sprint_metrics
    )
    return sprint
