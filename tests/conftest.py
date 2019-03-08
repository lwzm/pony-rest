from datetime import datetime

import pytest
from falcon.testing import TestClient

from pony_rest import make_application, application


@pytest.fixture(scope='session')
def client():
    #application = make_application()
    return TestClient(application)
