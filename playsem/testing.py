"""ponytail: test utilities, keep minimal."""

MockClient = type("MockClient", (), {"publish": lambda *args: None})()
