from unittest.mock import AsyncMock


def mock_lookup_db():
    class MockSubDb:
        def __getattr__(self, f_name):
            if f_name not in self.__dict__:
                self.__dict__[f_name] = AsyncMock()
            return self.__dict__[f_name]

    class MockDb:
        def __init__(self):
            self.subdbs_count = 0

        def __getattr__(self, name):
            if name not in self.__dict__:
                self.__dict__[name] = MockSubDb()
                self.subdbs_count += 1
            return self.__dict__[name]

    return MockDb()
