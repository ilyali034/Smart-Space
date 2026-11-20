class DeviceError(Exception):
    pass


class DeviceNotFound(DeviceError):
    def __init__(self, ref: object) -> None:
        super().__init__(f"device not found: {ref}")


class DeviceDisabled(DeviceError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"device is disabled: {slug}")


class DeviceAlreadyExists(DeviceError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"device with slug '{slug}' already exists")
        self.slug = slug


class DeviceRepositoryError(DeviceError):
    pass
