from datetime import datetime

import pytest
from falcon import testing
from pony.orm import Required, Optional

from pony_rest import BaseEntity, make_app, generate_mapping


@pytest.fixture(scope='session')
def client():
    class T(BaseEntity):
        s = Required(str)
        i = Optional(int)
        dt = Optional(datetime)

    generate_mapping()
    application = make_app()
    return testing.TestClient(application)
