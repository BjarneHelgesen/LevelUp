class ValidationResult:
    def __init__(self, file: str, valid: bool):
        self.file = file
        self.valid = valid

    def to_dict(self):
        return {
            'file': self.file,
            'valid': self.valid
        }
